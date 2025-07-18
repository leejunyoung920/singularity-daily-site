# fetch_all.py
import subprocess
import sys

def run_script(script):
    print(f"\n🚀 실행 중: {script} ...")
    try:
        result = subprocess.run([sys.executable, script], check=True)
        print(f"✅ 완료: {script}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 실패: {script} (exit code: {e.returncode})")

if __name__ == "__main__":
    run_script("scripts/rss_fetch.py")
    run_script("scripts/gmail_fetch_papers.py")
    run_script("scripts/collect_articles.py")
