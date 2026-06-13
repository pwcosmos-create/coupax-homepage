# SSH 키 복사본 위치 (배포용)

`%USERPROFILE%\.ssh` 안의 키를 **`board/deploy/local-ssh/`** 폴더에 복사해 두었습니다. 이 폴더는 **`.gitignore`에 들어 있어 Git에 올라가지 않습니다.** (비밀 키 유출 방지)

| 파일 | 용도 추정 |
|------|-----------|
| `shinserver.key` | 서버용 개인키 (이름 기준) |
| `oci_instance_key.pem` / `.pub` | OCI 인스턴스 SSH |
| `oci_a1_flex.pem` | OCI 관련 키 |
| `oci_instance_key_public.pem` | 공개키 PEM 형식 |
| `styleshimy-new-key` | 개인키 (확장자 없음) |
| `styleshimy-new-key.pub` | 공개키 |
| `ssh_config_copy` | 로컬 `~/.ssh/config` 복사본 (호스트·계정 정보 포함 가능) |

## 사용 예 (배포 zip 올릴 때)

PowerShell에서 실제 서버에 맞는 키를 지정하세요.

```powershell
# 예: OCI 키로 접속
scp -i "board\deploy\local-ssh\oci_instance_key.pem" board\coupax-board-deploy.zip opc@공인IP:/home/opc/

# 예: 다른 키
ssh -i "board\deploy\local-ssh\shinserver.key" ubuntu@공인IP
```

## 키를 다시 복사하려면

PowerShell:

```powershell
cd board\deploy
.\copy_ssh_keys_to_local.ps1
```

## 보안

- **이 폴더를 클라우드 동기화·메신저로 공유하지 마세요.**
- 원본은 항상 `C:\Users\<사용자명>\.ssh\` 입니다.
