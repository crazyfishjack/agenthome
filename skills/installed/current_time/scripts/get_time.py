import sys
import json
from datetime import datetime

def main():
    args = sys.argv[1:]
    
    format_type = "default"
    
    for i, arg in enumerate(args):
        if arg == "--format" and i + 1 < len(args):
            format_type = args[i + 1]
    
    now = datetime.now()
    
    if format_type == "iso":
        result = now.isoformat()
    elif format_type == "rfc":
        result = now.strftime("%a, %d %b %Y %H:%M:%S %z")
    elif format_type == "timestamp":
        result = str(int(now.timestamp()))
    elif format_type == "utc":
        result = datetime.utcnow().isoformat()
    else:
        result = now.strftime("%Y年%m月%d日 %H时%M分%S秒")
    
    print(result)
    
    output = {
        "time": result,
        "format": format_type,
        "timestamp": int(now.timestamp()),
        "utc": datetime.utcnow().isoformat()
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
