import os
from collections import Counter
import cv2
import glob
import re
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_dir", default="./")
parser.add_argument("-s", "--scale", default="960:540")
args = parser.parse_args()

def resizeCropInfo(key, cropPos, frame_width, frame_height):
    def _IsOutOfBound(_cropPos):
        w, h, x, y = _cropPos
        if (w + x) >= frame_width or (h + y) >= frame_height:
            return True
        if not all([a > 0 for a in _cropPos]):
            return True
    
    w, h, x, y = cropPos
    # Left (Expand width)
    if key == 0x250000:
        x -= 1
        w += 2
    # Right (Shrink width)
    elif key == 0x270000:
        x += 1
        w -= 2
    # Up (Expand height)
    elif key == 0x260000:
        y -= 1
        h += 2
    # Down (Shrink height)
    elif key == 0x280000:
        y += 1
        h -= 2
    # Num 4 (Move left)
    elif key == 52:
        x -= 1
        w -= 1
    # Num 6 (Move right)
    elif key == 54:
        w += 1
        x += 1
    # Num 8 (Move upward)
    elif key == 56:
        h -= 1
        y -= 1
    # Num 2 (Move downward)
    elif key == 50:
        h += 1
        y += 1
    _cropPos = w, h, x, y

    if not _IsOutOfBound(_cropPos):
        cropPos = _cropPos
    
        print("Current Crop Info : ", end="")
        print(cropPos, end="\r")

    return cropPos

# TODO:
# cropinfo 로그로 쓸수 있게 txt로 저장


def main():
    vid_paths = sorted(glob.glob(os.path.join(args.input_dir, '*.avi')))
    _scale = args.scale.split(":")
    if len(_scale) != 2 :
        print("Invalid target scale : ", args.scale)
        return

    target_width, target_height = [int(x) for x in _scale]
    
    if not ((target_width > 0) and (target_height > 0)):
        print("Invalid target scale : ", args.scale)
        return
    else :
        print("Input dir :", args.input_dir)
        print("Target scale: ", args.scale)

    for fpath in vid_paths:
        vid_name = os.path.basename(fpath)[:-4]
        # Debugging
        fpath = "01. Group S - I Swear MV.avi"

        print("File to detect crop: ", fpath)
        p = subprocess.Popen(["ffmpeg", "-ss", "30", "-i", fpath, "-vf", "cropdetect=limit=38:reset=30",
                             "-vframes", "1500", "-f", "null", "out.null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        infos = p.stderr.read().decode('utf-8')
        # print (infos)
        allCrops = re.findall("crop=\S+", infos)
        # print ("Crop Infos : ")
        # print (allCrops)
        mostCommonCrop = Counter(allCrops).most_common(1)
        print("most common detected crop info: %s" % mostCommonCrop)
        global crop
        crop = mostCommonCrop[0][0]

        cropPos = crop.split(":")
        # Delete "crop=" in list cropPos
        cropPos[0] = cropPos[0][5:]
        cropPos = [int(x) for x in cropPos]

        # Capture vid, Get width, height
        capture = cv2.VideoCapture(fpath)
        frame_width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        # Play speed : 33ms / frame
        while True:
            key = cv2.waitKeyEx(33)
            if key > 0 :
                # 27 == ESC
                if key == 27:
                    break

                cropPos = resizeCropInfo(key, cropPos, frame_width, frame_height)

            frame_pos = capture.get(cv2.CAP_PROP_POS_FRAMES)
            frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)

            if(frame_pos == frame_count):
                capture.open(vid)

            ret, frame = capture.read()

            cv2.rectangle(frame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                          cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
            # cv2.rectangle(frame, (4,43), (717,431), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
            cv2.imshow(f'{vid_name}', frame)

        capture.release()
        cv2.destroyAllWindows()

        # ffmpeg filter args
        crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]},"
        print(f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]},")

        if (target_height / target_height) >= (cropPos[0] / cropPos[1]):
            tmp_width = target_height * (cropPos[0] / cropPos[1])
            scale_arg = f"scale=w={tmp_width}:h={target_height},"
        else:
            tmp_height = target_width * (cropPos[1] / cropPos[0])
            scale_arg = f"scale=w={target_width}:h={tmp_height},"

        pad_arg = f"pad={target_width}:{target_height}:(ow-iw)/2:(ih-oh)/2,"

        print("Encoding \"%s\" ..." % vid_name)
        if False:
            p = subprocess.Popen(["ffmpeg", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y", "-pix_fmt",
                                 "yuv420p", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-loglevel", "error", f"_{vid_name}_cropped.mp4"])
        else:
            # for Debug
            p = subprocess.Popen(["ffmpeg", "-t", "15", "-ss", "30", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y",
                                 "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-loglevel", "error", f"_{vid_name}_cropped.mp4"])
        print("Encoding Done.")

        return


if __name__ == "__main__":
    main()
