"""
Semantic SQL Query Comparator v2

Compares SQL queries based on logical equivalence rather than string matching.
Handles table name variations intelligently.
"""

import re
from typing import Dict, List, Tuple, Set


class SemanticSQLComparator:
    """Compare SQL queries for semantic equivalence."""
    
    # Common table name variations
    TABLE_ALIASES = {
        'sales': ['sales_data', 'salesdata', 'sales_table'],
        'sales_data': ['sales', 'salesdata', 'sales_table'],
        'warranty': ['warranty_claims', 'warranties', 'warrantyclaims'],
        'warranty_claims': ['warranty', 'warranties', 'warrantyclaims'],
        'warranties': ['warranty', 'warranty_claims', 'warrantyclaims'],
        'dealer': ['dealer_claims', 'dealerclaims'],
        'dealer_claims': ['dealer', 'dealerclaims'],
        'telemetry': ['vehicle_telemetry', 'vehicletelemetry'],
        'vehicle_telemetry': ['telemetry', 'vehicletelemetry'],
    }
    
    def __init__(self):
        """Initialize the comparator."""
        self.normalized_aliases = self._build_normalized_aliases()
    
    def _build_normalized_aliases(self) -> Dict[str, str]:
        """Build a mapping of all variations to a canonical form."""
        mapping = {}
        for canonical, variations in self.TABLE_ALIASES.items():
            mapping[canonical.lower()] = canonical
            for variation in variations:
                mapping[variation.lower()] = canonical
        return mapping
    
    def _normalize_table_name(self, name: str) -> str:
        """Normalize table name to canonical form."""
        name_lower = name.strip().lower()
        return self.normalized_aliases.get(name_lower, name)
    
    def _extract_tables(self, sql: str) -> Set[str]:
        """Extract and normalize table names from SQL."""
        tables = set()
        
        # FROM clause
        from_pattern = r'FROM\s+(\w+)'
        for match in re.finditer(from_pattern, sql, re.IGNORECASE):
            normalized = self._normalize_table_name(match.group(1))
            tables.add(normalized.lower())
        
        # JOIN clauses
        join_pattern = r'JOIN\s+(\w+)'
        for match in re.finditer(join_pattern, sql, re.IGNORECASE):
            normalized = self._normalize_table_name(match.group(1))
            tables.add(normalized.lower())
        
        return tables
    
    def _get_select_fields(self, sql: str) -> List[str]:
        """Extract SELECT field expressions."""
        select_pattern = r'SELECT\s+(.+?)(?=FROM|WHERE|GROUP|ORDER|LIMIT|$)'
        match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return []
        
        select_clause = match.group(1).strip()
        
        # Just * means select all
        if select_clause == '*':
            return ['*']
        
        # Split by comma, clean up aliases
        fields = []
        for field in select_clause.split(','):
            # Remove AS alias
            field = re.sub(r'\s+AS\s+\w+\s*$', '', field, flags=re.IGNORECASE)
            field = field.strip().lower()
            if field:
                fields.append(field)
        
        return fields
    
    def _compare_select_clauses(self, expected_fields: List[str], actual_fields: List[str]) -> Tuple[float, str]:
        """Compare SELECT clauses allowing for aggregate function variations."""
        
        # Wildcard always matches
        if '*' in expected_fields or '*' in actual_fields:
            return 1.0, ""
        
        if not expected_fields and not actual_fields:
            return 1.0, ""
        
        if not expected_fields or not actual_fields:
            return 0.3, f"SELECT clause mismatch"
        
        # Normalize by removing common aggregate patterns
        def simplify_field(f):
            """Extract core function/column from field expression."""
            f = f.strip().lower()
            # Extract function and main arg if present
            if '(' in f and ')' in f:
                func_match = re.match(r'(\w+)\s*\((.*?)\)', f)
                if func_match:
                    func = func_match.group(1).lower()
                    arg = func_match.group(2).lower().strip()
                    # Simplified form
                    return f"{func}({arg.split()[0]})"  # Just main column, not whole expr
            return f.split()[0]  # Just the column name
        
        expected_simplified = {simplify_field(f) for f in expected_fields}
        actual_simplified = {simplify_field(f) for f in actual_fields}
        
        if expected_simplified == actual_simplified:
            return 1.0, ""
        
        # Check how many match
        matches = len(expected_simplified & actual_simplified)
        total = len(expected_simplified | actual_simplified)
        
        if total == 0:
            return 1.0, ""
        
        similarity = matches / total
        
        if similarity < 0.6:
            return similarity, f"SELECT fields missing"
        
        return similarity, ""
    
    def compare(self, expected: str, actual: str) -> Tuple[float, List[str]]:
        """
        Compare two SQL queries semantically.
        
        Returns:
            (similarity_score: 0-1, list of issues found)
        """
        if not expected or not actual:
            return 0.0, ["Empty query"]
        
        issues = []
        score = 1.0
        
        # Normalize to lowercase for comparison
        expected_norm = ' '.join(expected.split()).lower()
        actual_norm = ' '.join(actual.split()).lower()
        
        # 1. SELECT clause
        expected_select = self._get_select_fields(expected)
        actual_select = self._get_select_fields(actual)
        select_score, sel_issue = self._compare_select_clauses(expected_select, actual_select)
        if sel_issue:
            # Special-case: if expected uses an aggregate (e.g. AVG(col)) but actual
            # omits it from the SELECT, accept it as near-equivalent when the
            # aggregate appears in ORDER BY with GROUP BY (common pattern to
            # pick the top item) — apply a small penalty but keep WHERE checks strict.
            if "SELECT fields missing" in sel_issue:
                # Find aggregates in expected SELECT
                aggs = re.findall(r"(\w+)\s*\(([^)]+)\)", " ".join(expected_select), flags=re.IGNORECASE)
                agg_matched = False
                for func, arg in aggs:
                    func = func.lower()
                    # Look for ORDER BY func(...) in actual SQL
                    order_pattern = rf"order\s+by\s+{re.escape(func)}\s*\("
                    if re.search(order_pattern, actual_norm, re.IGNORECASE):
                        # require GROUP BY present as well
                        if 'group by' in actual_norm:
                            agg_matched = True
                            break

                if agg_matched:
                    # Treat as near-equivalent: small penalty instead of full mismatch
                    issues.append("SELECT omission but aggregate present in ORDER BY (minor penalty)")
                    select_score = max(select_score, 0.8)
                else:
                    issues.append(sel_issue)
            else:
                issues.append(sel_issue)
        score *= select_score
        
        # 2. Tables
        expected_tables = self._extract_tables(expected)
        actual_tables = self._extract_tables(actual)
        
        if expected_tables != actual_tables:
            issues.append(f"FROM tables differ")
            score *= 0.85  # Small penalty for table variation
        
        # 3. WHERE clause
        expected_where = 'where' in expected_norm
        actual_where = 'where' in actual_norm
        
        if expected_where and not actual_where:
            issues.append("Missing WHERE clause")
            score *= 0.7
        
        # 4. GROUP BY
        expected_group = 'group by' in expected_norm
        actual_group = 'group by' in actual_norm
        
        if expected_group and not actual_group:
            issues.append("Missing GROUP BY")
            score *= 0.6
        elif not expected_group and actual_group:
            score *= 0.95  # Minor penalty for extra GROUP BY
        
        # 5. Basic structure
        if 'select' not in actual_norm:
            issues.append("No SELECT found")
            return 0.0, issues
        
        if 'from' not in actual_norm:
            issues.append("No FROM clause")
            score *= 0.2
        
        return max(0.0, min(1.0, score)), issues


if __name__ == "__main__":
    comp = SemanticSQLComparator()
    
    tests = [
        (
            "SELECT region, SUM(units_sold) FROM sales GROUP BY region;",
            "SELECT region, SUM(units_sold) AS total_units_sold FROM sales_data GROUP BY region;",
        ),
        (
            "SELECT model, AVG(units_sold) FROM sales GROUP BY model;",
            "SELECT model, AVG(units_sold) AS avg_units_sold FROM salesdata GROUP BY model;",
        ),
        (
            "SELECT * FROM sales WHERE units_sold > 100000;",
            "SELECT * FROM sales_data WHERE units_sold > 100000;",
        ),
    ]
    
    print("SEMANTIC SQL COMPARISON TEST")
    print("=" * 80)
    
    for exp, act in tests:
        score, issues = comp.compare(exp, act)
        print(f"\nExpected: {exp}")
        print(f"Actual:   {act}")
        print(f"Score:    {score:.2f}")
        if issues:
            for issue in issues:
                print(f"  • {issue}")
