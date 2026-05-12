from pathlib import Path
import sys

import uvicorn


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parent / "backend"))
    print("Backend API:  http://127.0.0.1:8000/api/health")
    print("API docs:     http://127.0.0.1:8000/docs")
    print("Frontend UI:  http://127.0.0.1:8000")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
