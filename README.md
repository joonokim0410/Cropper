# Cropper
Convenient Vid cropping tool

## Info
- Window 용 Script
- 재생은 x3 배속으로 고정

## ivtc Code
< 하나의 파일을 변환하는 코드 >

ffmpeg -i in.mp4 -vf fieldmatch=mode=pc_n:combmatch=full,bwdif=0:-1:1,decimate -c:v libx264 -crf 0 -preset ultrafast out.mp4
 
< 폴더 내에 있는 모든 파일을 변환하는 코드 >

for %a in ("*.*") do ffmpeg -i "%a" -vf fieldmatch=mode=pc_n:combmatch=full,bwdif=0:-1:1,decimate -c:v libx264 -crf 0 -preset ultrafast ".\out\%~na_ivtc.mp4"

## ToDo
1. 우선 IVTC 파일이 1:1 매칭 되는 지 확인
2. 안되면 안된 파일들 목록 만들기
3. 만든 목록 파일들 IVTC 처리
4. 처리하는 동안 진행상황 Output
- **Concealing bitstream error** 해결
- ~~타이틀 창 등에 현재 재생 퍼센트 / 프레임 수 Display~~
- 타이틀 한글 깨지는 것
- 한 프레임씩 이동 하는 기능
- 처음에 목록 보여주고 시작? (필요한지?)
- Log Ouput 필요
    ### 포함 해야 할 내용
    - 날짜, 시간 정보 
    - 영상의 정보 (영상 파일명, 해상도, 길이, fps, 포맷)
    - Crop 정보 (W, H, X, Y)
    - 사용자가 Confirm 한 영상 TimeStamp (어디까지 보고 확인했는지에 대한 정보)
    - 소요된 Encoding 시간
    - Error 로그
        - File Missing (미구현)
        - FFMPEG Error (표시할 지 말지 결정해야 함)
            - 홀수값 입력
        - 추후 고려
    ### 로그 파일 포맷
    - Txt 파일 포맷
    - 영상 파일 명.txt
        - 같은 파일에 매 편집 시 누적되는 식
        - 각 편집 로그의 구별은 편집 시간정보별로.
### 구조적 문제
- Subprocess 기반으로 FFMPEG 동작
    - 현재 Encoding 중인 영상이 어느정도 진행 되었는 지 알 수 없음
    - 전체 프로그램이 종료되기 전까지는 파일이 생성되지 않음 (subprocess가 계속 돌고있는 듯 함)
    - 엔터를 누를 때 마다 다음 영상으로 넘어가기 때문에, 이전 영상의 진행도를 알기 어려울 듯 하다.
        - _생성되는 각 프로세스를 다른 변수명에 Mapping 하여 Log 관리를 각각 해야 하나?_
    - Encoding이 종료되면 프로세스를 종료시키는 것 같은 방법이 필요할듯..