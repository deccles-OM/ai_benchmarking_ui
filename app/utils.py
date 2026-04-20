"""
Utility functions for the Flask application.
Includes markdown conversion, process management, and other helpers.
"""
import sys
import subprocess
import re


def markdown_to_html(markdown_text):
    """Convert markdown text to HTML."""
    html = markdown_text
    
    # Remove standalone dashes (---)
    html = re.sub(r'^---+\s*$', '', html, flags=re.MULTILINE)
    
    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)
    
    # Code blocks
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # Process tables - convert markdown table format to HTML
    lines = html.split('\n')
    processed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a markdown table header line (contains |)
        if '|' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            # Check if next line is a separator line (contains | and -)
            if '|' in next_line and all(c in '|-' for c in next_line.replace(' ', '')):
                # This is a table! Extract headers and rows
                processed_lines.append('<table>')
                
                # Process header row
                headers = [h.strip() for h in line.split('|')[1:-1]]
                processed_lines.append('<thead><tr>')
                for header in headers:
                    processed_lines.append(f'<th>{header}</th>')
                processed_lines.append('</tr></thead>')
                
                # Skip the separator line
                i += 2
                
                # Process data rows
                processed_lines.append('<tbody>')
                while i < len(lines):
                    row_line = lines[i]
                    if '|' in row_line and not all(c in '|-' for c in row_line.replace(' ', '')):
                        cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
                        processed_lines.append('<tr>')
                        for cell in cells:
                            processed_lines.append(f'<td>{cell}</td>')
                        processed_lines.append('</tr>')
                        i += 1
                    else:
                        break
                
                processed_lines.append('</tbody>')
                processed_lines.append('</table>')
                continue
        
        processed_lines.append(line)
        i += 1
    
    lines = processed_lines
    
    # Line breaks and paragraphs
    html_lines = []
    in_list = False
    for line in lines:
        line = line.rstrip()
        if not line or line.startswith('<'):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if line and line.startswith('<'):
                html_lines.append(line)
            elif line:
                html_lines.append('<br>')
        elif line.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{line[2:]}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if line:
                html_lines.append(f'<p>{line}</p>')
    
    if in_list:
        html_lines.append('</ul>')
    
    html = '\n'.join(html_lines)
    
    # Wrap in basic HTML document
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark Results</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1, h2, h3, h4 {{
            color: #1F1E57;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        h1 {{
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 15px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        thead {{
            background: #1F1E57;
            color: white;
        }}
        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #667eea;
        }}
        td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        tbody tr:hover {{
            background: #f9f9f9;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background: #1F1E57;
            color: #e0e0e0;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            color: #e0e0e0;
            padding: 0;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 5px 0;
        }}
        strong {{
            color: #667eea;
            font-weight: 600;
        }}
        .metric {{
            display: inline-block;
            background: white;
            padding: 10px 15px;
            margin: 5px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .emoji {{
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
    
    return html_doc


def kill_stuck_processes():
    """Kill any stuck benchmark subprocess threads (not all Python processes).
    
    This function is called before starting a new benchmark to clean up any
    hung benchmark processes from previous runs.
    """
    try:
        # Look for any evaluate_benchmark_results.py subprocesses that might be hung
        if sys.platform == 'win32':
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/V', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and 'evaluate_benchmark' in line.lower():
                        # This is a hung evaluation subprocess, try to kill it
                        try:
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pid_str = parts[1].strip().strip('"')
                                pid = int(pid_str)
                                subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                                             capture_output=True, timeout=5)
                                print(f"[DEBUG] Killed stuck benchmark subprocess PID {pid}")
                        except (ValueError, subprocess.TimeoutExpired, IndexError):
                            pass
    except Exception as e:
        print(f"[DEBUG] Warning: Could not clean up benchmark subprocesses: {e}")
