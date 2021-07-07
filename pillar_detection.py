import io
from contextlib import redirect_stderr

import os
from collections import Counter
import cv2
import glob
import re
import subprocess
import argparse
import copy

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_dir", default="./", help="Input vid directory")
parser.add_argument("-o", "--output_dir", default="./out", help="Output vid directory")
parser.add_argument("-d", "--debug", default=False, action="store_true", help="for debugging. short output")
args = parser.parse_args()

def resizeCropInfo(key, cropPos, frame_width, frame_height):
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
        x -= 1
        w += 2
    # Right (Shrink width)
    elif key == ord('l') or key == ord('L'):
        x += 1
        w -= 2
    # Up (Expand height)
    elif key == ord('i') or key == ord('I'):
        y -= 1
        h += 2
    # Down (Shrink height)
    elif key == ord('k') or key == ord('K'):
        y += 1
        h -= 2
    # Num 4 (Move left)
    elif key == ord('a') or key == ord('A'):
        x -= 1
        w -= 1
    # Num 6 (Move right)
    elif key == ord('d') or key == ord('D'):
        w += 1
        x += 1
    # Num 8 (Move upward)
    elif key == ord('w') or key == ord('W'):
        h -= 1
        y -= 1
    # Num 2 (Move downward)
    elif key == ord('s') or key == ord('S'):
        h += 1
        y += 1
    _cropPos = w, h, x, y

    if not _IsOutOfBound(_cropPos):
        cropPos = _cropPos
    
        print("Current Crop Info : ", end="")
        print(cropPos, end="\r")

    return cropPos

def main():
    vid_types = ('*.avi', '*.mov', '*.mp4', '*.mxf')
    vid_grapped = []
    for types in vid_types :
        vid_grapped += sorted(glob.glob(os.path.join(args.input_dir, types)))

    #--------------------------------------------------------
    f = io.StringIO()
    #--------------------------------------------------------

    for fpath in vid_grapped:
        # debugging
        # fpath = "01. Group S - I Swear MV.avi"

        vid_name = os.path.basename(fpath)[:-4]


        print("File to detect crop: ", fpath)
        p = subprocess.Popen(["ffmpeg", "-ss", "10", "-i", fpath, "-vf", "cropdetect=limit=38",
                             "-vframes", "3000", "-f", "null", "out.null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        infos = p.stderr.read().decode('utf-8')
        # print (infos)
        allCrops = re.findall("crop=\S+", infos)
        # print ("Crop Infos : ")
        # print (allCrops)
        mostCommonCrop = Counter(allCrops).most_common(1)
        print("most common detected crop info: %s" % mostCommonCrop)
        global crop 
        crop = mostCommonCrop[0][0]

        # Delete "crop=" in list cropPos
        cropPos = crop.split(":")
        cropPos[0] = cropPos[0][5:]
        cropPos = [int(x) for x in cropPos]

        with redirect_stderr(f):
            # Capture vid, Get Vid info
            capture = cv2.VideoCapture(fpath)
            frame_width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            frame_height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = capture.get(cv2.CAP_PROP_FPS)
            frame_pos = 0
            frame_count = 0
            target_ratio = 16 / 9
            
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
    
            print("Target Ratio : %.5f" %target_ratio)
            print("Input dir :", args.input_dir)

            key = None
            isPaused = False
            pausedFrame = None
            frame = None
            cv2.namedWindow(f'{vid_name}')
            while True:
                key = cv2.waitKeyEx(10)

                # Handle close button event
                if cv2.getWindowProperty(f'{vid_name}', cv2.WND_PROP_VISIBLE) < 1 :
                    return

                if key > 0 :
                    # 13 == Enter key ASCII Code
                    if key == 13:
                        break
                    # Pause
                    elif key == ord('p') or key == ord('P'):
                        if isPaused :
                            isPaused = False
                        else :
                            isPaused = True
                            frame = copy.deepcopy(pausedFrame)
                    # Replay
                    elif key == ord('r') or key == ord('R'):
                        if not isPaused:
                            capture = cv2.VideoCapture(fpath)
                            continue
                    # Move Forward (10s)
                    elif key == ord('e') or key == ord('E'):
                        if not isPaused:
                            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos + (fps * 10))
                    # Move Backward (10s)
                    elif key == ord('q') or key == ord('Q'):
                        if not isPaused:
                            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos - (fps * 10))
                    else:
                        # Crop Area control
                        cropPos = resizeCropInfo(key, cropPos, frame_width, frame_height)

                frame_pos = capture.get(cv2.CAP_PROP_POS_FRAMES)
                frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)

                if(frame_pos >= frame_count):
                    break
                
                if not isPaused:
                    ret, frame = capture.read()
                    pausedFrame = copy.deepcopy(frame)
                    cv2.rectangle(frame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
                    cv2.imshow(f'{vid_name}', frame)    
                else :
                    pausedFrame = copy.deepcopy(frame)
                    cv2.rectangle(pausedFrame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=1, lineType=cv2.LINE_8)
                    cv2.imshow(f'{vid_name}', pausedFrame)
                

        capture.release()
        cv2.destroyAllWindows()

        # ffmpeg filter args
        crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]},"
        print(f"[CropInfo] (W : {cropPos[0]}), (H : {cropPos[1]}), (X : {cropPos[2]}), (Y : {cropPos[3]})")

        crop_ratio = cropPos[0] / cropPos[1]
        scale_arg = ""

        if target_ratio < crop_ratio:
            offset = (9 * cropPos[0] - 16 * cropPos[1]) / 16
            if int(offset) % 2 != 0:
                offset += 1
            tmp_height = cropPos[1] + offset
            # scale_arg = f"scale=w={cropPos[0]}:h={tmp_height},"
            pad_arg = f"pad={cropPos[0]}:{tmp_height}:(ow-iw)/2:(ih-oh)/2,"
        else:
            offset = (16 * cropPos[1] - 9 * cropPos[0]) / 9
            if int(offset) % 2 != 0:
                offset += 1
            tmp_width = cropPos[0] + offset
            # scale_arg = f"scale=w={tmp_width}:h={cropPos[1]},"
            pad_arg = f"pad={tmp_width}:{cropPos[1]}:(ow-iw)/2:(ih-oh)/2,"


        print("Encoding \"%s\" ..." % vid_name)

        if not os.path.exists(args.output_dir) :
            os.mkdir(args.output_dir)
            print(f'{args.output_dir} created')

        output_path = os.path.join(args.output_dir, f"{vid_name}_cropped.mp4")
        if args.debug:
            # for Debug
            p = subprocess.Popen(["ffmpeg", "-t", "15", "-ss", "30", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y",
                                 "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "0", "-preset", "medium", "-loglevel", "error", f"{output_path}"])
        else:
            p = subprocess.Popen(["ffmpeg", "-i", fpath, "-vf", crop_arg + scale_arg + pad_arg + "setsar=sar=1", "-y", "-pix_fmt",
                                 "yuv420p", "-c:v", "libx264", "-crf", "0", "-preset", "medium", "-loglevel", "error", f"{output_path}"])

        print("Encoding Done.")
        
        # debugging
        # return

if __name__ == "__main__":
    main()
