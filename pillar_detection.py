import os
from collections import Counter
import cv2
import glob
import re
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_dir", default="./")
args = parser.parse_args()

# cropdetect 에서 얻은 정보 => cv2로 그림 그리면서 confirm.

# confirm 안되면 w:h:x:y 를 콘솔로 정정할 수 있게 만듦 => 다시 confirm 시도
# confirm 되면 crop 진행 (resize는 일단 보류)

# cropinfo 로그로 쓸수 있게 txt로 저장

def main():
    # fpath = "01.mp4"
    fpath = "01. Group S - I Swear MV.avi"
    print ("File to detect crop: %s " % fpath)
    p = subprocess.Popen(["ffmpeg", "-ss", "30", "-i", fpath, "-vf", "cropdetect=limit=38:reset=30", "-vframes", "500", "-f", "rawvideo", "-y", "cropPos.mp4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    infos = p.stderr.read().decode('utf-8')
    # print (infos)
    # allCrops = re.findall(CROP_DETECT_LINE + ".*", infos)
    allCrops = re.findall("crop=\S+", infos)
    # print ("Crop Infos : ")
    # print (allCrops) 
    mostCommonCrop = Counter(allCrops).most_common(1)
    print ("most common crop: %s" % mostCommonCrop)
    global crop
    crop = mostCommonCrop[0][0]

    cropPos = crop.split(":")

    # delete "crop="
    cropPos[0] = cropPos[0][5:]

    cropPos = [int(x) for x in cropPos]

    vid_name = os.path.basename(fpath)
    capture = cv2.VideoCapture(fpath)

    # play speed : 33ms / frame
    while True:
        key = cv2.waitKeyEx(33)
        # 27 : ESC
        if key == 27:
            break
        # Left
        elif key == 0x250000:
            cropPos[2] -= 1
            cropPos[0] += 2
            print(cropPos)
        # Up
        elif key == 0x260000:
            cropPos[3] -= 1
            cropPos[1] += 2
            print(cropPos)
        # Right
        elif key == 0x270000:
            cropPos[0] -= 2
            cropPos[2] += 1
            print(cropPos)
        # Down
        elif key == 0x280000:
            cropPos[1] -= 2
            cropPos[3] += 1
            print(cropPos)
        # Num 4
        elif key == 52:
            cropPos[2] -= 1
            cropPos[0] -= 1
            print(cropPos)
        # Num 8
        elif key == 56:
            cropPos[3] -= 1
            cropPos[1] -= 1
            print(cropPos)
        # Num 6
        elif key == 54:
            cropPos[0] += 1
            cropPos[2] += 1
            print(cropPos)
        # Num 2
        elif key == 50:
            cropPos[1] += 1
            cropPos[3] += 1
            print(cropPos)

        frame_pos = capture.get(cv2.CAP_PROP_POS_FRAMES)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)

        if(frame_pos == frame_count):
            capture.open(vid)

        ret, frame = capture.read()
        
        cv2.rectangle(frame, (cropPos[2],cropPos[3]), (cropPos[2] + cropPos[0],cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
        # cv2.rectangle(frame, (2,45), (720,431), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
        cv2.imshow(f'{vid_name}', frame)

    capture.release()
    cv2.destroyAllWindows()

    p = subprocess.Popen(["ffplay", "-i", fpath, "-vf", f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == "__main__":
    main()