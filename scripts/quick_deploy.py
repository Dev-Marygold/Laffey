#!/usr/bin/env python3
"""
라피 봇 빠른 배포 스크립트
코드 수정 후 이 스크립트만 실행하면 자동으로 Heroku에 배포됩니다.
"""

import subprocess
import sys
import os

def run_command(command, description=""):
    """명령어를 실행하고 결과를 반환합니다."""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if result.returncode == 0:
            print(f"✅ {description} 완료")
            return True
        else:
            print(f"❌ {description} 실패:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ 명령어 실행 중 오류: {e}")
        return False

def main():
    print("🚀 라피 봇 빠른 배포 스크립트")
    print("=" * 50)
    
    # 1. 커밋 메시지 입력받기
    print("\n📝 배포할 내용을 설명해주세요:")
    commit_message = input("커밋 메시지: ").strip()
    
    if not commit_message:
        print("❌ 커밋 메시지를 입력해주세요.")
        return False
    
    print(f"\n🎯 커밋 메시지: '{commit_message}'")
    confirm = input("배포를 진행하시겠습니까? (y/n): ").strip().lower()
    
    if confirm not in ['y', 'yes', '예', 'ㅇ']:
        print("❌ 배포를 취소했습니다.")
        return False
    
    print("\n🔄 배포 시작...")
    
    # 2. Git 상태 확인
    if not run_command("git status", "Git 상태 확인"):
        return False
    
    # 3. 모든 변경사항 추가
    if not run_command("git add .", "변경사항 추가"):
        return False
    
    # 4. 커밋
    commit_cmd = f'git commit -m "{commit_message}"'
    if not run_command(commit_cmd, "변경사항 커밋"):
        # 커밋할 변경사항이 없는 경우 확인
        result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if not result.stdout.strip():
            print("ℹ️  커밋할 변경사항이 없습니다. 강제로 배포를 계속합니다.")
        else:
            print("❌ 커밋 실패. 수동으로 확인해주세요.")
            return False
    
    # 5. Heroku에 배포
    print("\n🚀 Heroku에 배포 중...")
    if not run_command("git push heroku main", "Heroku 배포"):
        print("❌ 배포에 실패했습니다.")
        print("💡 수동으로 'git push heroku main'을 실행해서 오류를 확인해주세요.")
        return False
    
    # 6. 배포 완료 확인
    print("\n🎉 배포 완료!")
    print("\n📊 배포 상태 확인 중...")
    
    # 다이노 상태 확인
    run_command("heroku ps", "다이노 상태 확인")
    
    print("\n✨ 배포가 성공적으로 완료되었습니다!")
    print("\n📝 유용한 명령어들:")
    print("   heroku logs --tail    # 실시간 로그 확인")
    print("   heroku ps            # 다이노 상태 확인")
    print("   heroku config        # 환경 변수 확인")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎊 라피 봇이 성공적으로 업데이트되었습니다!")
        else:
            print("\n😞 배포 중 문제가 발생했습니다.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  배포가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1) 