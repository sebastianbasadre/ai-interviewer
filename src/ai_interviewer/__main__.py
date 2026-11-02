"""Local single-worker launcher; access logs must never expose invitation tokens."""
import sys

from pydantic import ValidationError

from ai_interviewer.runtime import StartupError, build_app


def main() -> int:
    try:
        app = build_app()
    except StartupError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValidationError:
        print("Invalid configuration or role data; verify settings without logging secret values.", file=sys.stderr)
        return 2
    except Exception:
        print("Startup failed; verify role files and local storage permissions.", file=sys.stderr)
        return 2
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
