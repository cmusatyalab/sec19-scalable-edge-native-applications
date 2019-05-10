import subprocess
import os


SERVER = 'ubuntu@128.2.213.107'
ORIGINAL_PATH = '/home/junjuew/object-detection-web/demo-web/vatic/videos/'
NEW_PATH = '/home/ubuntu/c001-bk/20171022/junjuew/object-detection-web/demo-web/vatic/videos/'
OUTPUT_DIR = 'images'


def main():
    with open('train.txt') as f:
        for line in f:
            full_image_path = line.split()[1]
            image_path = full_image_path.replace(ORIGINAL_PATH, '')

            source_path = os.path.join(NEW_PATH, image_path)
            dest_path = os.path.join(OUTPUT_DIR, os.path.dirname(image_path))
            os.makedirs(dest_path, exist_ok=True)

            source = '{}:{}'.format(SERVER, source_path)
            subprocess.run(['scp', source, dest_path])


if __name__ == '__main__':
    main()
