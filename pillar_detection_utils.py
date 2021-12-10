import os
from collections import Counter
import cv2
import glob
import re
import subprocess
import argparse
import copy
import datetime
import time

def resizeCropInfo(key, cropPos, frame_width, frame_height):
# Adjust crop info in display layout.
    def _IsOutOfBound(_cropPos):
        w, h, x, y = _cropPos
        if (w + x) > frame_width or (h + y) > frame_height:
            return True
        if (x < 0) or (y < 0):
            return True
        if (w <= 0) or (h <= 0):
            return True
    
    w, h, x, y = cropPos
    # Left (Expand width)
    if key == ord('j') or key == ord('J'):
        x -= 2
        w += 4
    # Right (Shrink width)
    elif key == ord('l') or key == ord('L'):
        x += 2
        w -= 4
    # Up (Expand height)
    elif key == ord('i') or key == ord('I'):
        y -= 2
        h += 4
    # Down (Shrink height)
    elif key == ord('k') or key == ord('K'):
        y += 2
        h -= 4
    # Num 4 (Move left)
    elif key == ord('a') or key == ord('A'):
        # w -= 1
        x -= 1
    # Num 6 (Move right)
    elif key == ord('d') or key == ord('D'):
        # w += 1
        x += 1
    # Num 8 (Move upward)
    elif key == ord('w') or key == ord('W'):
        # h -= 1
        y -= 1
    # Num 2 (Move downward)
    elif key == ord('s') or key == ord('S'):
        # h += 1
        y += 1
    _cropPos = w, h, x, y

    if not _IsOutOfBound(_cropPos):
        cropPos = _cropPos

    return cropPos

def getTime():
    dt_now = datetime.datetime.now()
    dt_str = dt_now.strftime('[%Y-%m-%d %H:%M:%S]')
    # print(dt_str)

    return dt_str

def getVideDuration(file_path):
    ffprobe_command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"{file_path}\""
    p = subprocess.run(ffprobe_command, shell=False, stdout=subprocess.PIPE)
    _hour = 0
    _min = 0
    _sec = 0
    
    _sec = int(float(p.stdout.decode('utf-8')))
    # print(_sec)
    
    if _sec > 60 :
        _min = int(_sec // 60)
        _sec = _sec - (60 * _min)
        # print(_min, _sec)
    if _sec > 3600 : 
        _hour = int(_sec // 60)
        _sec = _sec - (60 * _min)
        _min = int(_sec // 60)
        _sec = _sec - (60 * _min)
        # print(_hour, _min, _sec)
    
    return [_hour, _min, _sec]

# for unicode free filename
def imwrite(filename, img, params=None): 
    try: 
        ext = os.path.splitext(filename)[1] 
        result, n = cv2.imencode(ext, img, params) 
        if result: 
            with open(filename, mode='w+b') as f: 
                n.tofile(f) 
                return True 
        else: 
            return False 
    except Exception as e: 
        print(e)
        return False
    
def parseLog(log_path, edit_mode, manual_mode, scale):
    cropPos = []
    
    if not os.path.exists(log_path):
        print(f"[INFO]\t Can`t find log file. [{log_path}]")
        manual_mode = True
        edit_mode = False
    else :
        print(f"[INFO]\t Loading log file... [{log_path}]")
        try :
            f = open(log_path, "r")
            logs = f.read()

            # if log file is not empty
            if logs != '':
                    # Delete "crop=" in list "crop"
                    allCrops = re.findall("crop=\S+", logs)
                    cropPos = allCrops[-1].split(":")
                    cropPos[0] = cropPos[0][5:]
                    print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
                    cropPos = [int(x * scale) for x in cropPos]
                    if scale > 1 :
                        print(f"[INFO]\t Scale up crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")

            else :
                print(f"[!!! WARNNIG !!!]\t Empty log file. [{log_path}]")
                manual_mode = True
                edit_mode = False
        except Exception as e:
            print(f"[!!! WARNNIG !!!]\t Can`t read log file. [{log_path}]")
            print(e)
            manual_mode = True
            edit_mode = False

        
    return cropPos, edit_mode, manual_mode

def writeLog(logs_dir, log_path, cropPos):
    if not os.path.exists(f"{logs_dir}"):
        print(f"[INFO]\t Make log directory [{log_path}]")
        os.makedirs(f"{logs_dir}")

    if not os.path.exists(f"{log_path}"):
        print(f"[INFO]\t Save log file in [{log_path}]")
        f = open(f"{log_path}", 'w')
    else :
        print(f"[INFO]\t Add line in log file [{log_path}]")
        f = open(f"{log_path}", 'a')

    dt_str = getTime()

    f.write(f"{dt_str}\tcrop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}\n")
    f.close

def autoDetectCropArea(fpath):
    cropPos = []
    
    print("[INFO]\t Detecting crop area...")
    p = subprocess.Popen(["ffmpeg", "-ss", "10", "-i", fpath, "-vf", "cropdetect=limit=38",
                        "-vframes", "3000", "-f", "null", "out.null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    infos = p.stderr.read().decode('utf-8')
    allCrops = re.findall("crop=\S+", infos)
    mostCommonCrop = Counter(allCrops).most_common(1)

    if len(mostCommonCrop) > 0 :
        crop = mostCommonCrop[0][0]
    else :
        print(f"[!!! ERROR !!!]\t Can`t read input vid. Skip to next vid \t ({fpath})")
        return cropPos

    # Delete "crop=" in list "crop"
    cropPos = crop.split(":")
    cropPos[0] = cropPos[0][5:]
    print(f"[INFO]\t Most common detected crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
    cropPos = [int(x) for x in cropPos]
    
    return cropPos

def adjustCropArea(cropPos):
    # Crop Area even num check
    if (cropPos[0] % 2) != 0 :
        if (cropPos[0] + 1) >= frame_width:
            cropPos[0] -= 1
        else:
            cropPos[0] += 1
    if (cropPos[1] % 2) != 0 :
        if (cropPos[1] + 1) >= frame_width:
            cropPos[1] -= 1
        else:
            cropPos[1] += 1

    # Crop Area Multiple of 4 check
    if (cropPos[0] % 4) != 0 :
        if (cropPos[0] + 2) >= frame_width:
            cropPos[0] -= 2
        else:
            cropPos[0] += 2
    if (cropPos[1] % 4) != 0 :
        if (cropPos[1] + 2) >= frame_width:
            cropPos[1] -= 2
        else:
            cropPos[1] += 2
            
    return cropPos

