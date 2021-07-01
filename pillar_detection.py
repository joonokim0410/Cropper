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


def resizeCropInfo(key, cropPos, frame_width, frame_height):
    def _IsOutOfBound(w, h, x, y):
        if (w + x) > frame_width or (h + y) > frame_height:
            return True

    # Left
    if key == 0x250000:
        cropPos[2] -= 1
        cropPos[0] += 2
    # Up
    elif key == 0x260000:
        cropPos[3] -= 1
        cropPos[1] += 2
    # Right
    elif key == 0x270000:
        cropPos[0] -= 2
        cropPos[2] += 1
    # Down
    elif key == 0x280000:
        cropPos[1] -= 2
        cropPos[3] += 1
    # Num 4
    elif key == 52:
        cropPos[2] -= 1
        cropPos[0] -= 1
    # Num 8
    elif key == 56:
        cropPos[3] -= 1
        cropPos[1] -= 1
    # Num 6
    elif key == 54:
        cropPos[0] += 1
        cropPos[2] += 1
    # Num 2
    elif key == 50:
        cropPos[1] += 1
        cropPos[3] += 1

    if cropPos[2] < 0 :
        cropPos[2] = 0
    if cropPos[3] < 0 :
        cropPos[3] = 0

    if key > 0:
        print(cropPos)
        
    return cropPos
    
# cropdetect 에서 얻은 정보 => cv2로 그림 그리면서 confirm.

# confirm 안되면 w:h:x:y 를 콘솔로 정정할 수 있게 만듦 => 다시 confirm 시도
# confirm 되면 crop 진행 (resize는 일단 보류)

# cropinfo 로그로 쓸수 있게 txt로 저장

def main():
    vid_paths = sorted(glob.glob(os.path.join(args.input_dir, '*.avi')))
    
    for fpath in vid_paths :
        vid_name = os.path.basename(fpath)
        fpath = "01. Group S - I Swear MV.avi"

        print ("File to detect crop: %s " % fpath)
        p = subprocess.Popen(["ffmpeg", "-ss", "30", "-i", fpath, "-vf", "cropdetect=limit=38:reset=30", "-vframes", "1500", "-f", "rawvideo", "-y", "cropPos.mp4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        infos = p.stderr.read().decode('utf-8')
        # print (infos)
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

        capture = cv2.VideoCapture(fpath)
        frame_width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # play speed : 33ms / frame
        while True:
            key = cv2.waitKeyEx(33)
            # 27 == ESC
            if key == 27:
                break

            resizeCropInfo(key, cropPos, frame_width, frame_height)

            frame_pos = capture.get(cv2.CAP_PROP_POS_FRAMES)
            frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)

            if(frame_pos == frame_count):
                capture.open(vid)

            ret, frame = capture.read()
            
            cv2.rectangle(frame, (cropPos[2],cropPos[3]), (cropPos[2] + cropPos[0],cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
            # cv2.rectangle(frame, (4,43), (717,431), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
            cv2.imshow(f'{vid_name}', frame)

        capture.release()
        cv2.destroyAllWindows()

        target_width = 960
        target_height = 540
        # ffmpeg filter args
        crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]},"
        print (f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]},")

        if (target_height / target_height) >= (cropPos[0] / cropPos[1]):
            tmp_width = target_height * (cropPos[0] / cropPos[1])
            scale_arg = f"scale=w={tmp_width}:h={target_height},"
        else:
            tmp_height = target_width * (cropPos[1] / cropPos[0])
            scale_arg = f"scale=w={target_width}:h={tmp_height},"
            
        pad_arg = f"pad={target_width}:{target_height}:(ow-iw)/2:(ih-oh)/2,"
        
        print("Encoding \"%s\"" %vid_name)
        if False:
            p = subprocess.Popen(["ffmpeg", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "15", "-preset", "medium","-loglevel", "error", f"_{vid_name}_cropped.mp4"])
        else:
            p = subprocess.Popen(["ffmpeg", "-t", "15", "-ss", "30", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "15", "-preset", "medium","-loglevel", "error", f"_{vid_name}_cropped.mp4"])
        

if __name__ == "__main__":
    main()