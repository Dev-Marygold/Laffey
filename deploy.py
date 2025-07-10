#!/usr/bin/env python3
"""
🚀 라피 봇 원클릭 헤로쿠 배포 스크립트
사용법: python deploy.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_cmd(command, description="", show_output=True):
    """명령어 실행"""
    if description:
        print(f"🔧 {description}")
    
    try:
        if show_output:
            result = subprocess.run(command, shell=True, check=True)
            return True
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"❌ 실패: {e}")
        return False

def check_requirements():
    """필수 요구사항 확인"""
    print("🔍 필수 요구사항 확인 중...")
    
    # Heroku CLI 확인
    success, stdout, stderr = run_cmd("heroku --version", show_output=False)
    if not success:
        print("❌ Heroku CLI가 설치되지 않았습니다.")
        print("💡 설치 명령어: brew install heroku/brew/heroku")
        return False
    
    # Git 확인
    success, stdout, stderr = run_cmd("git --version", show_output=False)
    if not success:
        print("❌ Git이 설치되지 않았습니다.")
        return False
    
    # .env 파일 확인
    if not Path(".env").exists():
        print("❌ .env 파일이 없습니다.")
        print("💡 .env 파일을 생성하고 필요한 환경 변수를 설정해주세요.")
        return False
    
    print("✅ 모든 요구사항이 충족되었습니다.")
    return True

def heroku_login():
    """헤로쿠 로그인 확인"""
    print("🔐 Heroku 로그인 확인 중...")
    success, stdout, stderr = run_cmd("heroku auth:whoami", show_output=False)
    
    if not success:
        print("🔑 Heroku에 로그인이 필요합니다.")
        if not run_cmd("heroku login", "Heroku 로그인"):
            return False
    else:
        print(f"✅ 로그인됨: {stdout.strip()}")
    
    return True

def create_or_connect_app():
    """앱 생성 또는 연결"""
    print("📱 Heroku 앱 확인 중...")
    
    # 기존 앱 연결 여부 확인
    success, stdout, stderr = run_cmd("heroku apps:info", show_output=False)
    
    if success:
        print("✅ 기존 Heroku 앱에 연결되어 있습니다.")
        return True
    
    # 앱 이름 입력받기
    print("🆕 새 Heroku 앱을 생성합니다.")
    app_name = input("앱 이름을 입력하세요 (엔터시 자동 생성): ").strip()
    
    if app_name:
        cmd = f"heroku create {app_name}"
    else:
        cmd = "heroku create"
    
    return run_cmd(cmd, "Heroku 앱 생성")

def setup_environment():
    """환경 변수 설정"""
    print("🔧 환경 변수 설정 중...")
    
    env_vars = {}
    
    # .env 파일 읽기
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value.strip().strip('"').strip("'")
    except Exception as e:
        print(f"❌ .env 파일 읽기 실패: {e}")
        return False
    
    # 필수 환경 변수 설정
    required_vars = [
        "DISCORD_TOKEN",
        "OPENAI_API_KEY", 
        "DEVELOPER_ID",
        "CREATOR_NAME",
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME",
        "PINECONE_ENVIRONMENT"
    ]
    
    for var in required_vars:
        if var in env_vars and env_vars[var]:
            success = run_cmd(f"heroku config:set {var}={env_vars[var]}", f"{var} 설정", show_output=False)
            if not success:
                print(f"❌ {var} 설정 실패")
                return False
        else:
            print(f"⚠️  {var} 환경 변수가 .env 파일에 없습니다.")
    
    print("✅ 환경 변수 설정 완료")
    return True

def deploy():
    """배포 실행"""
    print("🚀 Heroku에 배포 중...")
    
    # Git 변경사항 커밋
    run_cmd("git add .", "변경사항 추가", show_output=False)
    run_cmd('git commit -m "Deploy to Heroku"', "변경사항 커밋", show_output=False)
    
    # 헤로쿠에 배포
    if not run_cmd("git push heroku main", "Heroku 배포"):
        print("❌ 배포 실패")
        return False
    
    # 워커 다이노 활성화
    if not run_cmd("heroku ps:scale worker=1", "워커 다이노 활성화"):
        print("⚠️  워커 다이노 활성화 실패 (수동으로 활성화 필요)")
    
    print("✅ 배포 완료!")
    return True

def main():
    """메인 함수"""
    print("🤖 라피 봇 원클릭 헤로쿠 배포")
    print("=" * 40)
    
    # 1. 요구사항 확인
    if not check_requirements():
        sys.exit(1)
    
    # 2. 헤로쿠 로그인
    if not heroku_login():
        sys.exit(1)
    
    # 3. 앱 생성/연결
    if not create_or_connect_app():
        sys.exit(1)
    
    # 4. 환경 변수 설정
    if not setup_environment():
        sys.exit(1)
    
    # 5. 배포
    if not deploy():
        sys.exit(1)
    
    # 6. 완료 메시지
    print("\n🎉 배포 완료!")
    print("\n📊 유용한 명령어:")
    print("  heroku logs --tail     # 실시간 로그")
    print("  heroku ps              # 다이노 상태")
    print("  heroku config          # 환경 변수")
    print("  heroku apps:info       # 앱 정보")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  배포가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1) 