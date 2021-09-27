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

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input_dir", default="./input", help="Input source vid directory")
# parser.add_argument("-i", "--ivtc_dir", default="./0729_work/ivtc", help="Input ivtc vid directory")
parser.add_argument("-o", "--output_dir", default="./out", help="Output vid directory")
parser.add_argument("-c", "--crf", default=15, type=int, help="set crf level")
parser.add_argument("-lb", "--add_letterbox", default=False, action="store_true", help="adding letterbox to make 16:9 ratio")
parser.add_argument("-uhd", "--uhd_output", default=False, action="store_true", help="set output resolution to 3840:2160")
parser.add_argument("-mul", "--multi_encoding", default=3, type=int, help="when log file exist, encoding mutiple videos by this args")
parser.add_argument("-s", "--cropsize_scale", default=1, type=int, help="before use crop size from logfile, scale up")
parser.add_argument("-log", "--only_logfile", default=False, action="store_true", help="large vid mode. (only write log file.)")
parser.add_argument("-man", "--manual_mode", default=False, action="store_true", help="manual cropping without using log file (Ignore log files)")
parser.add_argument("-edit", "--edit_mode", default=False, action="store_true", help="get first crop area from log file")
parser.add_argument("-d", "--debug", default=False, action="store_true", help="for debugging. (short length video output)")
args = parser.parse_args()

# Adjust crop info in display layout.
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

def main():
    vid_types = ('*.avi', '*.mov', '*.mp4', '*.mxf')

    # video encoding opts
    input_dir = args.input_dir
    crf = args.crf
    add_letterbox = args.add_letterbox
    uhd_output = args.uhd_output

    # program modes
    multi_how_many = args.multi_encoding - 1
    scale =  int(args.cropsize_scale)
    only_logfile = args.only_logfile
    manual_mode = args.manual_mode
    debug = args.debug
    edit_mode = args.edit_mode

    if scale < 1 :
        print(f"[!!! ERROR !!!]\t Invalid scale option [scale : {scale}]")
        return
    elif multi_how_many < 1 :
        print(f"[!!! ERROR !!!]\t Invalid multi_encoding option [multi_encoding : {multi_how_many}]")
        return

    uhd_output_args = ""
    if uhd_output :
        uhd_output_args = "-s 3840x2160"

    debug_shortOutput = ""
    if debug :
        debug_shortOutput = "-t 15 -ss 30"

    # ivtc_dir = args.ivtc_dir
    output_dir = args.output_dir
    
    t = time.time

    input_list = []
    # ivtc_list = []
    for types in vid_types :
        input_list += sorted(glob.glob(os.path.join(input_dir, types)))

    """
    File cross check codes. [deprecated, 07/30]
    Compare "args.source_dir", "args.ivtc_dir" 
    check difference of two input, make ivtc version of source_dir videos.
    """
    # ivtc_list += sorted(glob.glob(os.path.join(ivtc_dir, "*.mp4")))

    # if len(ivtc_list) > 0:
    #     ivtc_input_list = []
    #     for i, fpath in enumerate(source_list):
    #         vid_name = os.path.basename(fpath)[:-4]
    #         ivtc_name_list = [os.path.basename(x)[:-4] for x in ivtc_list]

    #         if not vid_name + "_ivtc" in ivtc_name_list :
    #             ivtc_input_list += glob.glob(fpath)
    #             print(f"[INFO]\t Seems \"{os.path.basename(fpath)}\" is stil telecine... add to ivtc processing list")
    # else :
    #     ivtc_input_list = source_list

    # for i, ivtc_input in enumerate(ivtc_input_list) :
    #     ivtc_input_num = len(ivtc_input_list)
    #     ivtc_input_name = os.path.basename(ivtc_input)
    #     ivtc_output_path = os.path.join(ivtc_dir, ivtc_input_name[:-4]) + "_ivtc.mp4"

    #     if not os.path.exists(ivtc_dir) :
    #         os.mkdir(ivtc_dir)
    #         print(f'[INFO]\t {ivtc_dir} created')
        
    #     print(f"[INFO]\t Work ivtc on \"{ivtc_input_name}\" ===> \"{ivtc_output_path}\" ... [{i + 1}/{ivtc_input_num}]")
    #     print("[INFO]\t Please wait...")
    #     start_time = time.time()
    #     subprocess.run(["ffmpeg", "-ss", "10", "-i", ivtc_input, "-vf", "fieldmatch=mode=pc_n:combmatch=full,bwdif=0:-1:1,decimate", "-c:v", "libx264", "-crf", f"{crf}",
    #                     "-preset", "ultrafast","-loglevel", "quiet", "-y", ivtc_output_path])
    #     t = time.time() - start_time
    #     print("[INFO]\t Work done. [It takes %.2f seconds.]" % t)
    # ivtc_dir = []
    # ivtc_dir += sorted(glob.glob(os.path.join(ivtc_dir, "*.mp4")))
    # print("[INFO]\t Input ivtc dir :", ivtc_dir)

    print("[INFO]\t Input dir :", input_dir)
    for index, fpath in enumerate(input_list):
        vid_name = os.path.basename(fpath)[:-4]
        vid_num = len(input_list)
        isSkipped = False
        logs = ''

        # Read log file if exist
        if not manual_mode:
            if not os.path.exists(f"./logs/{vid_name}.txt"):
                print(f"[INFO]\t Can`t find log file. [./logs/{vid_name}.txt]")
                edit_mode = False
            else :
                print(f"[INFO]\t Loading log file... [./logs/{vid_name}.txt]")
                f = open(f"./logs/{vid_name}.txt", "r")
                logs = f.read()

                if logs != '':
                    try :
                        # Delete "crop=" in list "crop"
                        allCrops = re.findall("crop=\S+", logs)
                        cropPos = allCrops[-1].split(":")
                        cropPos[0] = cropPos[0][5:]
                        print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
                        cropPos = [int(x * scale) for x in cropPos]
                        if scale > 1 :
                            print(f"[INFO]\t Scale up crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")

                    except:
                        print(f"[!!! WARNNIG !!!]\t Can`t read log file. [./logs/{vid_name}.txt]")

                else :
                    print(f"[!!! WARNNIG !!!]\t Empty log file. [./logs/{vid_name}.txt]")

        if (logs == '') or manual_mode or edit_mode:
            # TODO : Korean title text bug fix
            # vid_name = vid_name.encode('utf-8').decode('cp949')

            print(f"[INFO]\t Video num : {index + 1} / {vid_num}")
            print("[INFO]\t File to detect crop area: ", fpath)
            if edit_mode:
                print("[INFO]\t (Edit mode) Read crop area from log file...")
                print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
            else :
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
                    continue

                # Delete "crop=" in list "crop"
                cropPos = crop.split(":")
                cropPos[0] = cropPos[0][5:]
                print(f"[INFO]\t Most common detected crop area: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
                cropPos = [int(x) for x in cropPos]

            # Capture vid, Get Vid info
            capture = cv2.VideoCapture(fpath)
            frame_width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            frame_height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = capture.get(cv2.CAP_PROP_FPS)
            frame_pos = 0
            frame_count = 0
            
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

            key = None
            isPaused = False
            pausedFrame = None
            frame = None

            cv2.namedWindow(f'{vid_name}', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)

            # Display crop size control UI
            while True:
                key = cv2.waitKeyEx(10)

                # Close button(X button) event
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
                    # Display key guide
                    elif key == ord('h') or key == ord('H'):
                        print("[INFO]\t ### KEY GUIDE ########################################################################################################")
                        print("[INFO]\t #  (MOVE : wasd), (RESIZE : ijkl), (FOR / BACKWARD : q, e), (RESET : r), (PAUSE : p), (SKIP : n), (CONFIRM : enter)  #")
                        print("[INFO]\t ###################################################################################################################### ")
                    # Skip this Vid
                    elif key == ord('n') or key == ord('N'):
                        print(f"[INFO]\t Skip this video")
                        isSkipped = True
                        break;
                    elif key == ord('v') or key == ord('V'):
                        _x = cropPos[2]
                        _y = cropPos[3]
                        _w = cropPos[0]
                        _h = cropPos[1]
                        _frame = copy.deepcopy(pausedFrame)
                        cv2.namedWindow(f'{vid_name}_current_area', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
                        cv2.waitKey(10)
                        cv2.imshow(f'{vid_name}_current_area', _frame[_y: (_y + _h), _x: (_x + _w)])
                        # cv2.imshow(f'{vid_name}_current_area', _frame[0: int(frame_height), 0: int(frame_width)])
                        # cv2.imshow(f'{vid_name}_current_area', _frame[0: int(100), 0: int(100)])
                        
                    else:
                        # Crop Area control
                        cropPos = resizeCropInfo(key, cropPos, frame_width, frame_height)

                frame_pos = capture.get(cv2.CAP_PROP_POS_FRAMES)
                frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
                
                if(frame_pos >= frame_count):
                    break

                print("[INFO]\t Current crop area : ", end="")
                print(cropPos, end="")
                print(f"\t Frame Count ({frame_pos}/{frame_count})\t[PRESS \"h\" TO VIEW KEY GUIDE]", end="\r")

                # When paused, hold current frame untill unpause.
                if isPaused:
                    # deep copy current frame, use that frame for draw rectangle.
                    pausedFrame = copy.deepcopy(frame)
                    cv2.rectangle(pausedFrame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=2, lineType=cv2.LINE_8)
                    cv2.imshow(f'{vid_name}', pausedFrame)
                else :
                    ret, frame = capture.read()
                    # deep copy current frame for pausing process.
                    pausedFrame = copy.deepcopy(frame)
                    cv2.rectangle(frame, (cropPos[2], cropPos[3]), (cropPos[2] + cropPos[0],
                            cropPos[3] + cropPos[1]), (0, 0, 255), thickness=2, lineType=cv2.LINE_8)    
                    cv2.imshow(f'{vid_name}', frame)    
                    
            print("")
            capture.release()
            cv2.destroyAllWindows()

            # Debugging
            # cropPos[0] = 678
            # cropPos[1] = 402
            # cropPos[2] = 20
            # cropPos[3] = 38
            # pad_arg = ""

            dt_str = getTime()

            if not isSkipped:
                if not os.path.exists("./logs"):
                    print(f"[INFO]\t Make log directory [./logs/{vid_name}.txt]")
                    os.makedirs("./logs")

                if not os.path.exists(f"./logs/{vid_name}.txt"):
                    print(f"[INFO]\t Save log file in [./logs/{vid_name}.txt]")
                    f = open(f"./logs/{vid_name}.txt", 'w')
                else :
                    print(f"[INFO]\t Add line in log file [./logs/{vid_name}.txt]")
                    f = open(f"./logs/{vid_name}.txt", 'a')

                f.write(f"{dt_str}\tcrop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}\n")
                f.close

        # Set ffmpeg commands, actual ffmpeg encoding
        if not (only_logfile or isSkipped):
            crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"
            print(f"[INFO]\t [CropInfo] (W : {cropPos[0]}), (H : {cropPos[1]}), (X : {cropPos[2]}), (Y : {cropPos[3]})")

            crop_arg = f"crop={cropPos[0]}:{cropPos[1]}:{cropPos[2]}:{cropPos[3]}"
            current_crop_ratio = cropPos[0] / cropPos[1]
            scale_arg = ""
            pad_arg = ""

            """
            Set padding(letter box) argument
            variable "offset" for 16:9 output display ratio

            pad_arg syntax:
                pad= {width after padding}:{height after padding}:{x offset of pad}:{y offset of pad}
            """
            if add_letterbox :
                # Always target 16:9 display ratio
                target_ratio = 16 / 9
                print("[INFO]\t Target ratio : %.7f" %target_ratio)

                if target_ratio < current_crop_ratio:
                    offset = (9 * cropPos[0] - 16 * cropPos[1]) / 16
                    tmp_height = cropPos[1] + offset
                    tmp_height = int(tmp_height)
                    if (tmp_height % 4) != 0:
                        tmp_height -= (tmp_height % 4)
                    pad_arg = f",pad={cropPos[0]}:{tmp_height}:(ow-iw)/2:(ih-oh)/2"
                    scale_arg = f",scale=w={cropPos[0]}:h={tmp_height}"
                    print(f"[INFO]\t [PadInfo] (W : {cropPos[0]}), (H : {tmp_height})")
                else:
                    offset = (16 * cropPos[1] - 9 * cropPos[0]) / 9
                    tmp_width = cropPos[0] + offset
                    tmp_width = int(tmp_width)
                    if (tmp_width % 4) != 0:
                        tmp_width -= (tmp_width % 4)
                    pad_arg = f",pad={tmp_width}:{cropPos[1]}:(ow-iw)/2:(ih-oh)/2"
                    scale_arg = f",scale=w={tmp_width}:h={cropPos[1]}"
                    print(f"[INFO]\t [PadInfo] (W : {tmp_width}), (H : {cropPos[1]})")

            

            if not os.path.exists(output_dir) :
                os.mkdir(output_dir)
                print(f'[INFO]\t {output_dir} created')

            output_path = os.path.join(output_dir, f"{vid_name}_box.mov")
            
            ## ffmpeg command setting
            ffmpeg_command = f"ffmpeg {debug_shortOutput} -i \"{fpath}\" -vf \"{crop_arg}{scale_arg}{pad_arg}\" -y -pix_fmt yuv420p -c:v libx264 -crf {crf} -c:a copy -preset medium -loglevel error {uhd_output_args} \"{output_path}\""
            print(ffmpeg_command)
            print("[INFO]\t Encoding \"%s\" ..." % vid_name)    
            print("[INFO]\t Video CRF = %d" % int(crf))

            if (logs == '') or manual_mode:
                # Manual Mode (always encoding one by one)
                # Hold process when encoding last video 
                if (index + 1) == vid_num :
                    p = subprocess.run(ffmpeg_command, shell=True)
                else :
                    p = subprocess.Popen(ffmpeg_command, shell=True)
            else:
                # Log file mode (encoding simultaneously 5 videos)
                if (index % multi_how_many == 0) and (index != 0) or ((index + 1) == vid_num):
                    p = subprocess.run(ffmpeg_command, shell=True)
                else :
                    p = subprocess.Popen(ffmpeg_command, shell=True)

if __name__ == "__main__":
    main()
    print("[INFO]\t Program End.")
