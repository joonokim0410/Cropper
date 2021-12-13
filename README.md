# Cropper
Convenient Vid cropping tool

## Info
- Window 용 python Script
- 재생은 x3 배속으로 고정

## ToDo
- N/A
### 구조적 문제
- Subprocess 기반으로 FFMPEG 동작
    - 현재 Encoding 중인 영상이 어느정도 진행 되었는 지 알 수 없음
    - 전체 프로그램이 종료되기 전까지는 파일이 생성되지 않음 (subprocess가 계속 돌고있게 됨)
