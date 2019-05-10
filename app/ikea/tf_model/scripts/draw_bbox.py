from object_detection.utils import visualization_utils as vis_util
from PIL import Image


IMAGE = 'images/2_blackcircle_21.mp4/0/0/0.jpg'
LABEL = 'labels/0.txt'


def main():
    image = Image.open(IMAGE)
    width, height = image.size

    with open(LABEL, 'r') as f:
        for line in f:
            contents = line.split()
            pixel_xmin = int(contents[0])
            pixel_ymin = int(contents[1])
            pixel_width = int(contents[2])
            pixel_height = int(contents[3])
            label = contents[4]

            xmin = pixel_xmin / width
            ymin = pixel_ymin / height
            xmax = (pixel_xmin + pixel_width) / width
            ymax = (pixel_ymin + pixel_height) / height

            vis_util.draw_bounding_box_on_image(
                image,
                ymin,
                xmin,
                ymax,
                xmax,
                display_str_list=[label])

    image.show()


if __name__ == '__main__':
    main()
