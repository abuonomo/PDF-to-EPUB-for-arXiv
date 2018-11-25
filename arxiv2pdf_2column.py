import pdf2image as p2i
from PIL import Image as im
import numpy as np
import shutil
import zipfile
import os


out_dir = 'C:\\Users\\yourname\\Desktop\\'
pdf = 'C:\\Users\\yourname\\Desktop\\somefile.pdf'

screen_h=1872
screen_w=1404


def crop(tpage, step = 10):
    vline = 0 # SIDE CROP (assuming right/left margins the same)
    while np.mean(tpage[:,-vline]) == 0:
        vline += step
    vline -= 20
    tpage[:,:vline] = 0 # remove the ugly side thing
    top_crop = step # CROP THE TOP
    while np.mean(tpage[top_crop,:]) == 0:
        top_crop += step
    top_crop -= 20 # CROP THE BOTTOM
    bot_crop = tpage.shape[0] - step
    while np.mean(tpage[bot_crop,:]) == 0:
        bot_crop -= step
    bot_crop += 20
    tpage = tpage[top_crop:bot_crop,vline:-vline]
    return tpage


def try_v_split(tpage, page_slices):
    screen_ratio = screen_h / screen_w
    mid_line = tpage.shape[1]//2
    middle = tpage[:,mid_line]
    if np.mean(middle) > 0:
        indices = np.where(middle>0)[0]
        box_end = min(indices.max() + 20, tpage.shape[0])
        while np.mean(tpage[box_end,:]) > 0:
            box_end += 5
    if np.mean(middle) == 0:
        box_end = 0
    # now if there is a box in the middle we take it out
    # if it exists, we add it to the page_slices list (scope otuside this function)
    if box_end != 0:
        box = tpage[:box_end,:]
        # decide whether box fits on page or to slice it
        to_cut_box = (box.shape[0]/box.shape[1]) > screen_ratio
        if to_cut_box:
            half_box = box.shape[0]//2
            box1 = box[:half_box,:]
            box2 = box[half_box:,:]
            page_slices.append(np.transpose(box1[:,::-1]))
            page_slices.append(np.transpose(box2[:,::-1]))
            print('did half box ')
        if not to_cut_box:
            page_slices.append(np.transpose(box[:,::-1]))
        tpage = tpage[box_end:,:]
    left_side = tpage[:,:mid_line]
    rite_side = tpage[:,mid_line:]
    return left_side, rite_side


def slice_2col(mpage,line_space=25,screen_h=1872,screen_w=1404):
    screen_ratio = screen_h / screen_w

    mpage_width = mpage.shape[1] # height needs to be at most 1.33*width
    max_height = screen_ratio * mpage_width
    mpage_height = mpage.shape[0]
    needed_slices = int(np.ceil(mpage_height / max_height))
    # QUALITY VERSION -> find a cuttable line near the middle
    # LAZY VERSION -> just cut anywhere and give extra space
    # Using lazy version because it is exception-proof (like say there is an image in teh middle that's a bit too long)
    slices = []
    slice_height = mpage_height / needed_slices
    for i in range(needed_slices):
        slice_bot = int(max(0, slice_height*i-line_space))
        slice_top = int(min(slice_height*(i+1)+line_space, mpage_height))
        a_slice = mpage[slice_bot:slice_top]
        slices.append(a_slice)
    return slices


def make_epub(images, output_dir, title=None, author=None):
    if True:

        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>
        '''

        page_xml_1 = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?><html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <title>Strength</title>

        <meta content="http://www.w3.org/1999/xhtml; charset=utf-8" http-equiv="Content-Type"/>

                <style title="override_css" type="text/css">
                    body { text-align: center; padding:0pt; margin: 0pt; }
                </style>
            </head>
            <body>
                <div>
                    <svg xmlns="http://www.w3.org/2000/svg" height="100%" version="1.1" width="100%" xmlns:xlink="http://www.w3.org/1999/xlink">
                        <image xlink:href="../Images/'''

        page_xml_2 = '''.jpg"/>
                    </svg>
                </div>
            </body>
        </html>
        '''
        page_xml_1 + '0000' + page_xml_2

        content1 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
        <package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uuid_id" version="2.0">
            <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:opf="http://www.idpf.org/2007/opf" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

                <dc:title>{title}</dc:title>

                <dc:language>en</dc:language>

                <dc:identifier id="uuid_id" opf:scheme="uuid">isbn-000-0-000-00000-0</dc:identifier>
                <dc:creator>{author}</dc:creator>
                <dc:publisher>Swagu Booksu</dc:publisher>
                <dc:date>2099-09-09</dc:date>

                <meta name="cover" content="my-cover-image"/>

            </metadata>
            <manifest>
        '''

        add_manifest = '''
                <item href="Text/{xhtml_file}.xhtml" id="{xhtml_id}" media-type="application/xhtml+xml"/>
                <item href="Images/{image_file}.jpg" id="{image_id}" media-type="image/jpeg"/>
        '''

        content2 = '''
            </manifest>
            <spine toc="tableofcontents">
        '''


        add_spine = '''
                <itemref idref="{0}"/>
        '''

        content3 = '''
            </spine>
            <guide>
                <reference href="Text/bookcover.xhtml" title="Cover Image" type="cover"/>
            </guide>
        </package>
        '''

    epub = zipfile.ZipFile(output_dir + title + '.epub', 'w')
    epub.writestr("mimetype", "application/epub+zip")
    epub.writestr("META-INF/container.xml", container_xml)

    manifest, spine = '', ''

    names = [format(i, '04d')  for i in range(len(images))]

    # Write first image due to some exceptions
    im_content = open(images[0], 'rb').read()
    epub.writestr("OEBPS/Images/" + 'cover.jpg', im_content)

    manifest += content1.format(title=title, author=author)
    manifest += add_manifest.format(xhtml_file = 'bookcover',
                                    image_file = 'cover.jpg',
                                    xhtml_id = 'bookcover',
                                    image_id = 'my-cover-image')
    spine += '        <itemref idref="bookcover" linear="no"/>'
    im_content2 = page_xml_1 + 'cover' + page_xml_2
    epub.writestr("OEBPS/Text/bookcover.xhtml", im_content2)

    for index in range(1, len(images[1:])):
        image = images[index]
        image_name = names[index]
        im_content = open(image, 'rb').read()

        epub.writestr("OEBPS/Images/" + image_name + '.jpg', im_content)
        xhtml_id = 'idk' + image_name
        manifest += add_manifest.format(xhtml_file = xhtml_id,
                                        image_file = image_name,
                                        xhtml_id = xhtml_id,
                                        image_id = image_name)
        spine += add_spine.format(xhtml_id)
        im_content2 = page_xml_1 + image_name + page_xml_2
        epub.writestr("OEBPS/Text/{0}.xhtml".format(xhtml_id), im_content2)

    manifest += content2
    manifest += spine
    manifest += content3
    epub.writestr("OEBPS/content.opf", manifest)
    epub.close()


def pdf2epub(pdf=pdf, out_dir=out_dir):
    pdf_title = pdf.split('\\')[-1].split('.pdf')[0]
    # Create a temporary working directory
    temp_dir_name = out_dir + 'temp'
    while os.path.exists(temp_dir_name):
        temp_dir_name += '0'
    temp_dir_name += '\\'
    os.mkdir(temp_dir_name)

    # Convert PDF document to images
    screen_ratio = screen_h / screen_w
    data = p2i.convert_from_path(pdf, fmt='png', thread_count=8)

    # Slice images into smaller ones
    all_slices = []
    for i in range(len(data)):
        tpage = 255 - np.asarray(data[i])[:,:,0]

        page_slices = []
        tpage = crop(tpage)
        left_side, rite_side = try_v_split(tpage, all_slices)

        left_slices = slice_2col(left_side)
        rite_slices = slice_2col(rite_side)

        page_slices += left_slices
        page_slices += rite_slices

        all_slices += page_slices


    digits = len(str(len(all_slices)))
    file_names = [str(i).rjust(digits, '0') + '.jpg' for i in range(len(all_slices))]
    for index, slice in enumerate(all_slices):
        im.fromarray(255-slice).save(temp_dir_name + file_names[index])

    # Convert JPEG images to EPUB
    images = [temp_dir_name + i for i in os.listdir(temp_dir_name)]
    make_epub(images, title = pdf_title, output_dir = out_dir)

    shutil.rmtree(temp_dir_name)




if __name__ == "__main__":
    pdf2epub(pdf, out_dir)