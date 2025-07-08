#!/usr/bin/env python3
"""
Heroku 배포 자동화 스크립트
로컬 .env 파일에서 환경 변수를 읽어와서 Heroku에 설정합니다.
"""

import os
import subprocess
import sys
from pathlib import Path

# 필요한 환경 변수 목록
REQUIRED_VARS = [
    "DISCORD_TOKEN",
    "OPENAI_API_KEY",
    "DEVELOPER_ID",
    "CREATOR_NAME",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "PINECONE_ENVIRONMENT"
]

def load_env_file(env_path=".env"):
    """
    .env 파일을 로드하여 환경 변수 딕셔너리를 반환합니다.
    """
    env_vars = {}
    
    if not Path(env_path).exists():
        print(f"❌ {env_path} 파일을 찾을 수 없습니다.")
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 따옴표 제거
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
        
        print(f"✅ {env_path} 파일에서 {len(env_vars)}개의 환경 변수를 로드했습니다.")
        return env_vars
    
    except Exception as e:
        print(f"❌ {env_path} 파일을 읽는 중 오류 발생: {e}")
        return env_vars

def run_command(command, capture_output=False):
    """
    명령어를 실행하고 결과를 반환합니다.
    """
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(command, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_heroku_cli():
    """
    Heroku CLI가 설치되어 있는지 확인합니다.
    """
    success, stdout, stderr = run_command("heroku --version", capture_output=True)
    if success:
        print(f"✅ Heroku CLI 설치 확인: {stdout}")
        return True
    else:
        print("❌ Heroku CLI가 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요: brew install heroku/brew/heroku")
        return False

def check_heroku_login():
    """
    Heroku에 로그인되어 있는지 확인합니다.
    """
    success, stdout, stderr = run_command("heroku auth:whoami", capture_output=True)
    if success:
        print(f"✅ Heroku 로그인 확인: {stdout}")
        return True
    else:
        print("❌ Heroku에 로그인되지 않았습니다.")
        print("다음 명령어로 로그인하세요: heroku login")
        return False

def check_heroku_app():
    """
    Heroku 앱이 연결되어 있는지 확인합니다.
    """
    success, stdout, stderr = run_command("heroku apps:info", capture_output=True)
    if success:
        print("✅ Heroku 앱 연결 확인")
        return True
    else:
        print("❌ Heroku 앱이 연결되지 않았습니다.")
        print("다음 명령어로 앱을 생성하세요: heroku create your-app-name")
        return False

def set_heroku_config(env_vars):
    """
    환경 변수를 Heroku에 설정합니다.
    """
    missing_vars = []
    
    # 필수 변수 확인
    for var in REQUIRED_VARS:
        if var not in env_vars or not env_vars[var]:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 필수 환경 변수가 누락되었습니다: {', '.join(missing_vars)}")
        return False
    
    print("🔧 Heroku 환경 변수 설정 중...")
    
    # 환경 변수 설정
    for var in REQUIRED_VARS:
        if var in env_vars:
            command = f"heroku config:set {var}={env_vars[var]}"
            success, stdout, stderr = run_command(command, capture_output=True)
            if success:
                print(f"✅ {var} 설정 완료")
            else:
                print(f"❌ {var} 설정 실패: {stderr}")
                return False
    
    print("✅ 모든 환경 변수 설정 완료!")
    return True

def deploy_to_heroku():
    """
    Heroku에 배포합니다.
    """
    print("🚀 Heroku에 배포 중...")
    
    # Git 상태 확인
    success, stdout, stderr = run_command("git status --porcelain", capture_output=True)
    if stdout:
        print("📝 변경 사항을 커밋합니다...")
        run_command("git add .")
        run_command('git commit -m "Ready for Heroku deployment"')
    
    # 배포
    success, stdout, stderr = run_command("git push heroku main")
    if success:
        print("✅ 배포 완료!")
        return True
    else:
        print(f"❌ 배포 실패: {stderr}")
        return False

def scale_worker():
    """
    워커 다이노를 활성화합니다.
    """
    print("⚙️ 워커 다이노 활성화 중...")
    success, stdout, stderr = run_command("heroku ps:scale worker=1")
    if success:
        print("✅ 워커 다이노 활성화 완료!")
        return True
    else:
        print(f"❌ 워커 다이노 활성화 실패: {stderr}")
        return False

def main():
    """
    메인 함수
    """
    print("🤖 라미 봇 Heroku 배포 자동화 스크립트")
    print("=" * 50)
    
    # 1. 전제 조건 확인
    print("\n1️⃣ 전제 조건 확인")
    if not check_heroku_cli():
        sys.exit(1)
    
    if not check_heroku_login():
        sys.exit(1)
    
    if not check_heroku_app():
        sys.exit(1)
    
    # 2. 환경 변수 로드
    print("\n2️⃣ 환경 변수 로드")
    env_vars = load_env_file()
    if not env_vars:
        sys.exit(1)
    
    # 3. 환경 변수 설정
    print("\n3️⃣ Heroku 환경 변수 설정")
    if not set_heroku_config(env_vars):
        sys.exit(1)
    
    # 4. 배포
    print("\n4️⃣ Heroku 배포")
    if not deploy_to_heroku():
        sys.exit(1)
    
    # 5. 워커 활성화
    print("\n5️⃣ 워커 다이노 활성화")
    if not scale_worker():
        sys.exit(1)
    
    # 6. 완료
    print("\n🎉 배포 완료!")
    print("📱 다음 명령어로 로그를 확인하세요:")
    print("   heroku logs --tail")
    print("🌐 앱 URL:")
    run_command("heroku apps:info | grep 'Web URL'")

if __name__ == "__main__":
    main() 