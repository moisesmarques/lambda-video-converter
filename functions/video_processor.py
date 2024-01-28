import os
import tempfile
import uuid
import boto3
import ffmpeg
from math import ceil
import ffmpeg_streaming
from ffmpeg_streaming import Formats, Bitrate, Representation, Size

accepted_codecs = ["h264"]
accepted_resolutions = ["1920x1080", "1080x1920", "1280x720", "720x1280"]
minimum_frame_rate = 30
maximum_frame_rate = 60
minimum_bitrate = 128000
maximum_bitrate = 320000000
minimum_duration = 2 # in seconds
maximum_duration = 300 # in seconds

S3_BUCKET = os.getenv('S3_BUCKET')

def handler(event, context):

    for record in event['Records']:
        
        origin_file_path = record['s3']['object']['key']
        
        s3 = boto3.client( 's3')
        temp_dir = tempfile.gettempdir()
        input_temp_path = os.path.join(temp_dir, str(uuid.uuid4()))
        
        s3.download_file(S3_BUCKET, origin_file_path, input_temp_path)
        
        specs = ffmpeg.probe(input_temp_path)["streams"]
        
        if not check_video_has_all_specs(specs):
            print("Uploaded file has no specs")
            return

        validation = check_all(specs[0])

        if len(validation) > 0:
            print(validation)
            return
            
        video = ffmpeg_streaming.input(input_temp_path)

        dash = video.dash(Formats.h264())

        _720p = None
        _1080p = None

        if specs[0]["width"] > specs[0]["height"]:
            _720p = Representation(Size(1280, 720), Bitrate(2048 * 1024, 320 * 1024)) 
        else:
            _720p = Representation(Size(720, 1280), Bitrate(2048 * 1024, 320 * 1024))
        
        if specs[0]["width"] > specs[0]["height"]:
            _1080p = Representation(Size(1920, 1080), Bitrate(4096 * 1024, 320 * 1024))
        else:
            _1080p = Representation(Size(1080, 1920), Bitrate(4096 * 1024, 320 * 1024))

        dash.representations(_720p, _1080p)

        output_path = os.path.join(temp_dir, str(uuid.uuid4()))
        os.makedirs(output_path, exist_ok=True)
        dash.output(f'{output_path}/stream.mpd')

        # upload the streams to s3
        for stream in os.listdir(output_path):
            file_path = os.path.join(output_path, stream)
            s3.upload_file(file_path, S3_BUCKET, f'videos/{origin_file_name}/{stream}')
        
        print("Video processed successfuly")

def check_codec(specs):
    codec = specs["codec_name"]
    if codec not in accepted_codecs:
        return False
    return True

def check_resolution(specs):
    resolution = "%sx%s" % (specs["width"], specs["height"])
    if resolution not in accepted_resolutions:
        return False
    return True

def get_frame_rate(specs):
    avg_frame_rate = specs["avg_frame_rate"]
    avg_frame_rate = avg_frame_rate.split("/")
    avg_frame_rate = int(avg_frame_rate[0]) / int(avg_frame_rate[1])
    avg_frame_rate = ceil(avg_frame_rate)
    return avg_frame_rate

def check_avg_frame_rate(specs):
    avg_frame_rate = get_frame_rate(specs)
    if avg_frame_rate < minimum_frame_rate or avg_frame_rate > maximum_frame_rate:
        return False
    return True

def check_bitrate(specs):
    bitrate = specs["bit_rate"]
    bitrate = int(bitrate)
    if bitrate < minimum_bitrate or bitrate > maximum_bitrate:
        return False
    return True

def check_duration(specs):
    duration = float(specs["duration"])
    if duration < minimum_duration or duration > maximum_duration:
        return False
    return True

def check_video_has_all_specs(specs):
    if type(specs) is not list or len(specs) == 0:
        return False   
    
    specs = specs[0]
    needed_specs = ["codec_name", "width", "height", "avg_frame_rate", "bit_rate", "duration"]
    for spec in needed_specs:
        if spec not in specs:
            return False
    return True

def check_all(specs):
    not_passed = []

    if not check_codec(specs):
        not_passed.append({"spec": "codec", "value": specs["codec_name"], "accepted": accepted_codecs})
    if not check_resolution(specs):
        not_passed.append({"spec": "resolution", "value": "%sx%s" % (specs["width"], specs["height"]), "accepted": accepted_resolutions})
    if not check_avg_frame_rate(specs):
        not_passed.append({"spec": "frame_rate", "value": get_frame_rate(specs), "accepted": "%s-%s" % (minimum_frame_rate, maximum_frame_rate)})
    if not check_bitrate(specs):
        not_passed.append({"spec": "bitrate", "value": specs["bit_rate"], "accepted": "%s-%s" % (minimum_bitrate, maximum_bitrate)})
    if not check_duration(specs):
        not_passed.append({"spec": "duration", "value": specs["duration"], "accepted": "%s-%s" % (minimum_duration, maximum_duration)})

    return not_passed