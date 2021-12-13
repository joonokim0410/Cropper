from pillar_detection_utils import *
from pillar_detection_core import *

parser = argparse.ArgumentParser()
# file path options
parser.add_argument("-i", "--input_dir", default="./input", help="Input source vid directory")
parser.add_argument("-o", "--output_dir", default="./out", help="Output vid directory")

# ffmpeg encoding option
parser.add_argument("-c", "--crf", default=20, type=int, help="set crf level")
parser.add_argument("-uhd", "--uhd_output", default=False, action="store_true", help="set output resolution to 3840:2160")
parser.add_argument("-lb", "--add_letterbox", default=False, action="store_true", help="add letterbox to make 16:9 ratio")
parser.add_argument("-sp", "--add_sharpening", default=False, action="store_true", help="add ffmpeg sharpening filter")
parser.add_argument("-mul", "--multi_encoding", default=2, type=int, help="when log file exist, encoding mutiple videos by this args")
parser.add_argument("-d", "--debug", default=False, action="store_true", help="for debugging. (short length video output)")

# logfile option
parser.add_argument("-s", "--cropsize_scale", default=1, type=int, help="before use crop size from logfile, scale up the crop size (for reuse when vid rescaled)")
parser.add_argument("-log", "--only_logfile", default=False, action="store_true", help="large vid mode. (only write log file.)")
parser.add_argument("-man", "--manual_mode", default=False, action="store_true", help="manual cropping without using log file (Ignore log files)")
parser.add_argument("-edit", "--edit_mode", default=False, action="store_true", help="get first crop area from log file")

args = parser.parse_args()

# option when only write log file (no encoding) : -log
# options when only edit log file that already exists (no encoding) : -log -edit

def main():
    vid_types = ('*.avi', '*.mov', '*.mp4', '*.mxf')
    manual_mode = args.manual_mode
    edit_mode = args.edit_mode
    input_dir = args.input_dir
    output_dir = args.output_dir
    logs_dir = input_dir

    if args.cropsize_scale < 1 :
        print(f"[!!! ERROR !!!]\t Invalid scale option [scale : {args.cropsize_scale}]")
        return
    elif args.multi_encoding < 1 :
        print(f"[!!! WARRNING !!!]\t \"multi_encoding\" option should be more then 0 [multi_encoding : {args.multi_encoding}]")
        return

    input_list = []
    for types in vid_types :
        input_list += glob.glob(os.path.join(input_dir, types))
    input_list = sorted(input_list)
    print("[INFO]\t Input dir :", input_dir)
    print("[INFO]\t Ouput dir :", output_dir)
    print("")
    
    for vid_index, fpath in enumerate(input_list):
        vid_name = os.path.basename(fpath)[:-4]
        vid_num = len(input_list)
        isSkipped = False
        log_path = f"{logs_dir}/{vid_name}.txt"
        print(f"[INFO]\t [Video num : {vid_index + 1} / {vid_num}]")
        print("[INFO]\t File path: ", fpath)
        print("[INFO]\t Log dir :", logs_dir)

        # init crop configuration class
        crop_cfg = VideoCropCfg()
        crop_cfg.vid_name = vid_name
        
        # Read log file if exist
        if not manual_mode:
            cropPos, edit_mode, manual_mode = parseLog(log_path, edit_mode, manual_mode, args.cropsize_scale)

        if manual_mode or edit_mode:
            # Capture vid, Get Vid info
            crop_cfg.getVidInfo(fpath)
            
            if edit_mode:
                print("[INFO]\t (Edit mode) Read crop area from log file...")
                print(f"[INFO]\t Crop area from log file: [w : {cropPos[0]}, h : {cropPos[1]}, x : {cropPos[2]}, y : {cropPos[3]}]")
            else :
                cropPos = autoDetectCropArea(fpath)
            # Crop Area validation check (width, height must be even number)
            cropPos = adjustCropArea(cropPos)

            cv2.namedWindow(f'{vid_name}', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            # Display crop size control UI
            while True:
                retCode, cropPos = video_croppping(crop_cfg, cropPos)
                if retCode == 1:
                    break
                elif retCode == 2:
                    crop_cfg.getVidInfo(fpath)
                    continue
            print("")
                    
            crop_cfg.vidRelease()
            cv2.destroyAllWindows()

            if not isSkipped:
                writeLog(logs_dir, log_path, cropPos)

        # Set ffmpeg commands, actual ffmpeg encoding
        if not (args.only_logfile or isSkipped):
            ffmpeg_encoding(args, vid_index, vid_num, cropPos, vid_name, fpath)

if __name__ == "__main__":
    main()
    print("[INFO]\t Program End.")
