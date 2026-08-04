# GitHub ↔ Obsidian 자동 동기화 설정

이 문서는 로컬 Obsidian에서 쓴 노트가 **별도로 손대지 않아도** 자동으로 GitHub(`mynotes` 저장소)에 저장되도록 설정하는 방법입니다.
아래 과정은 딱 한 번, **본인 컴퓨터/휴대폰에서** 진행하시면 됩니다. (클라우드 세션이 대신 해줄 수 없는 부분입니다 — 로컬 기기의 인증 정보와 로컬 Obsidian 앱 설정이라서요.)

---

## 1단계. 저장소 clone (아직 안 했다면)

```bash
git clone https://github.com/goldgarden9620419-maker/mynotes.git
```

Obsidian 앱에서 **"Open folder as vault"**로 이 clone된 폴더를 엽니다.

## 2단계. git 인증 설정 (자동 push를 위해 꼭 필요)

자동 push가 되려면 컴퓨터가 비밀번호 없이 GitHub에 push할 수 있어야 합니다. 둘 중 하나를 선택하세요.

**옵션 A — Personal Access Token (가장 간단, 데스크톱+모바일 모두 가능)**
1. GitHub → 우측 상단 프로필 → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token
2. Repository access를 `mynotes` 저장소로 제한하고, **Contents: Read and write** 권한만 부여
3. 생성된 토큰을 복사 (한 번만 보여줌 — 안전한 곳에 잠깐 메모)
4. 터미널에서 한 번 push 시도하면 username/password를 물어보는데, **password 자리에 토큰을 입력**
   ```bash
   git push
   # Username: <GitHub 아이디>
   # Password: <복사한 토큰>
   ```
   이후 OS의 credential manager(Windows: Credential Manager, Mac: Keychain)에 저장되어 다음부턴 자동으로 인증됩니다.

**옵션 B — SSH 키 (터미널에 익숙하다면 더 편함)**
```bash
ssh-keygen -t ed25519 -C "goldgarden9620419@gmail.com"
cat ~/.ssh/id_ed25519.pub   # 출력된 내용을 복사
```
GitHub → Settings → SSH and GPG keys → New SSH key에 붙여넣기 후, 저장소 원격 주소를 SSH로 변경:
```bash
git remote set-url origin git@github.com:goldgarden9620419-maker/mynotes.git
```

## 3단계. Obsidian에 "Git" 플러그인 설치

1. Obsidian 설정(⚙️) → **Community plugins** → "Turn on community plugins" (경고 문구가 뜨는데, 신뢰할 수 있는 공식 플러그인이니 동의)
2. **Browse** → 검색창에 `Git` 입력 → 제작자 **Vinzent03**의 "Git" 플러그인 선택 → Install → Enable

> 이 플러그인은 25만+ 다운로드된 Obsidian 공식 커뮤니티 플러그인 목록에 등재된 검증된 플러그인입니다.

## 4단계. 자동 백업 주기 설정

플러그인 설정(⚙️ → Git) 들어가서 아래 값들을 설정하세요:

| 설정 항목 | 추천 값 | 효과 |
|---|---|---|
| **Vault backup interval (minutes)** | `10` | 10분마다 변경사항을 자동 commit + push |
| **Auto pull interval (minutes)** | `10` | 10분마다 다른 기기에서 올린 변경사항을 자동으로 받아옴 |
| **Auto pull on boot** | ON | Obsidian 켤 때마다 최신 상태로 자동 동기화 |
| **Commit message on manual backup/on auto backup** | `vault backup: {{date}}` | 커밋 메시지에 자동으로 날짜 기록 |
| **Pull changes before push** | ON | push 전에 항상 최신 내용 먼저 받아서 충돌 방지 |

설정 후에는 노트를 쓰고 저장만 하면, 신경 안 써도 10분마다 알아서 GitHub에 백업됩니다.

## 5단계. (선택) 모바일에서도 쓰기

iOS/Android Obsidian 앱에서도 Git 플러그인 설치 가능합니다. 다만 모바일은 SSH가 까다로우니 **옵션 A(토큰)** 방식을 추천하며, 플러그인 설정에서 "Personal access token" 입력란에 위에서 만든 토큰을 넣어주면 됩니다.

---

## 동작 원리 요약

```
[Obsidian 앱에서 노트 작성/저장]
        │
        ▼  (Git 플러그인이 주기적으로 감지)
[자동 git commit]
        │
        ▼
[자동 git push] ──────► [GitHub의 mynotes 저장소]
        ▲
        │  (다른 기기는 auto pull로 반대 방향 동기화)
[다른 기기의 Obsidian 앱]
```

이 설정을 마치면, "코드를 만들거나 이 클라우드 세션에서 작업한 내용"은 제가 커밋+push로 저장하고, "직접 로컬 Obsidian 앱에서 쓴 노트"는 Git 플러그인이 자동으로 저장 — 양쪽 다 손 안 대고 GitHub에 반영됩니다.
