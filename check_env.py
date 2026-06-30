import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, ".env")

with open("env_check_log.txt", "w", encoding="utf-8") as out:
    out.write(f"Current Dir: {current_dir}\n")
    out.write(f"Dotenv Path: {dotenv_path}\n")
    out.write(f"Dotenv Path Exists: {os.path.exists(dotenv_path)}\n")

    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            out.write("--- File Contents ---\n")
            out.write(f.read())
            out.write("\n---------------------\n")

    success = load_dotenv(dotenv_path, override=True)
    out.write(f"load_dotenv success: {success}\n")
    out.write(f"BOT_TOKEN env: '{os.getenv('BOT_TOKEN')}'\n")
    out.write(f"ADMIN_ID env: '{os.getenv('ADMIN_ID')}'\n")

print("Diagnostics complete. Output written to env_check_log.txt")
