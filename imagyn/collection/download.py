"""
MIT License

Copyright (c) 2017 Zev Isert; Jose Gordillo; Matt Hodgson; Graeme Turney; Maxwell Borden

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
Contains classes and functions regarding downloading the images.
"""

import requests
import multiprocessing

import os
import io
import uuid
import shutil
import random

from itertools import repeat
from PIL import Image, ImageChops

from imagyn.collection import lexicon
from imagyn.collection.utils import binary_images


class Downloader:
    def __init__(self):
        """
        Contains various image download functions.
        """
        self.lexicon = lexicon.SynsetLexicon()

    def download_sequential(self, urls, destination, prefix):
        """
        Download images in sequentially in one process.
        :param urls: list of urls to download
        :param destination: Location to store downloaded images
        :param prefix: synset id or descriptor word for urls
        :return: List of images downloaded successfully
        """

        retrieved = []

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)

        # Loop over the images to retrieve
        for url in urls:
            # Retrieve the url at the next index
            filename = self.download_single_checked(
                url=url,
                destination=destination,
                prefix=prefix
            )
            if filename is not None:
                retrieved.append(filename)

        return retrieved

    def download_multiple_synsets(self, count, synsets, destination, sequential=False):
        """
        Download images from multiple synsets.
        :param count: Number of images to attempt to sample from each synset
        :param synsets: List of synsets to request images from
        :param destination: Location to store the downloaded files
        :param sequential: Use sequential (single threaded) download method
        :return: Dict of lists of images downloaded from each synset
        """

        downloaded_files = dict()
        downloader = self.download_sequential if sequential else self.multidownload

        # If there are a very small number of images to be retrieved then just use first synset
        calculated_count = count // len(synsets)
        if calculated_count == 0:
            sid = self.lexicon.get_synset_id(synsets[0])

            if len(self.lexicon.API.words_for(sid)) > 0:
                prefix = self.lexicon.API.words_for(sid)[0].replace(" ", "_")
            else:
                prefix = ""

            downloaded_files[sid] = downloader(
                urls=random.sample(self.lexicon.API.urls_for(sid), count),
                destination=destination,
                prefix=prefix
            )

        # otherwise go through each synset and try to get the number of images required
        else:
            for synset in synsets:
                sid = self.lexicon.get_synset_id(synset)

                if len(self.lexicon.API.words_for(sid)) > 0:
                    prefix = self.lexicon.API.words_for(sid)[0].replace(" ", "_")
                else:
                    prefix = ""

                downloaded_files[sid] = downloader(
                    urls=random.sample(self.lexicon.API.urls_for(sid), count),
                    destination=destination,
                    prefix=prefix
                )

        return downloaded_files

    def download_synset_by_id(self, max_images, synset_ids, destination, sequential=False):
        """
        Download images from a synset.
        :param max_images: Max number of images to attempt to download from a synset (0 for all)
        :param synset_ids: List of synset_ids to request images from
        :param destination: Location to store the downloaded files
        :param sequential: Use sequential (single threaded) download method
        :return: Dict of lists of images downloaded from each synset
        """

        downloaded_files = dict()
        downloader = self.download_sequential if sequential else self.multidownload

        for synset_id in synset_ids:

            if len(self.lexicon.API.words_for(synset_id)) > 0:
                prefix = self.lexicon.API.words_for(synset_id)[0].replace(" ", "_")
            else:
                prefix = ""

            urls=self.lexicon.API.urls_for(synset_id)
            if max_images and (len(urls)>max_images):
                urls = urls[:max_images]
            
            downloaded_files[synset_id] = downloader(
                urls=urls,
                destination=destination,
                prefix=prefix
            )

        return downloaded_files

    def multidownload(self, urls: list, destination: str, prefix: str):
        """
        Use several processes to speed up image acquisition.
        :param urls: list of urls to attempt to download
        :param destination: folder to put images in
        :param prefix: synset id or descriptor word of urls
        :return: List of images names downloaded successfully
        """
        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)

        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            # Returns number of images downloaded
            return list(
                filter(
                    lambda res: res is not None,
                    pool.starmap(self.download_single_checked, zip(urls, repeat(destination), repeat(prefix)))
                )
            )

    def download_single_checked(self, url: str, destination: str, prefix: str):
        """
        Download a single image, checking for failure cases.
        :param url: Url to attempt to download an image from
        :param destination: folder to store downloaded image in
        :param prefix: synset id or descriptor word for url
        :return: Filename or None as success if downloaded succeeded
        """
        # splits to (`url+filename`, `.`, `filesuffix`)
        filetype = url.strip().rpartition('.')[2]
        keep = None

        # We need a naming scheme that won't overwrite anything
        # Option a) pass in the index with the url
        # Option b) use a sufficiently sized random number
        #   > Only after generating 1 billion UUIDs every second for the next 100 years,
        #   > the prob of creating just one duplicate would be about 50%.
        #   > The prob of one duplicate would be about 50% if every person on earth owns 600 million UUIDs.
        file = os.path.join(destination, '{}-{}.{}'.format(prefix, uuid.uuid4(), filetype))

        try:
            # require either .png, .jpg, or .jpeg
            if filetype in ['png', 'jpg', 'jpeg']:

                # Get the file
                response = requests.get(url, stream=True, timeout=5)
                if response.status_code == 200:
                    with open(file, 'wb') as out_file:
                        response.raw.decode_content = True
                        shutil.copyfileobj(response.raw, out_file)
                        keep = False  # None -> False :: We have a file now, need to verify

                    # Check we got an image not some HTML junk 404
                    with Image.open(file) as img:
                        # Logic here is that if we can interpret the image then its good
                        # PIL is lazy - the raster data isn't loaded until needed or `load` is called explicitly'
                        keep = True  # False -> True :: We've decided to keep the download

                        # Look through the known 'not available images'
                        for bin_image in binary_images.values():

                            # If this image size matches
                            if img.size == bin_image['size']:

                                # Compare the raster data
                                with Image.open(io.BytesIO(bin_image['raster'])) as raster:
                                    if ImageChops.difference(raster, img).getbbox() is None:
                                        # No bounding box for the difference of these images, so
                                        # this is a 'image not availble' image
                                        keep = False  # True -> False :: Changed our mind..

        # If anything above failed we're not keeping this one
        except:
            keep = False
        finally:
            if keep is None or keep is False:
                if os.path.isfile(file):
                    os.remove(file)
            else:
                return file  # Return the name of the downloaded file, otherwise implicit return None

    def main(self):
        """ download.py """

        parser = argparse.ArgumentParser(description="Imagyn Image Downloader")

        parser.add_argument(
            "-n", "--number",
            type=int,
            default=1,
            help="Number of images to attempt to download"
        )

        parser.add_argument(
            "keyword",
            type=str,
            help="Keyword to search for"
        )

        parser.add_argument(
            "output_dir",
            type=str,
            action=IsRWDir,
            help="Output directory for downloaded images"
        )

        parser.add_argument(
            "-v", "--verbosity",
            type=int,
            choices=[0, 1, 2],
            default=1
        )

        args = parser.parse_args()

        synset = self.lexicon.get_synset(keyword=args.keyword)
        wnid = self.lexicon.get_synset_id(synset)
        urls = self.lexicon.API.urls_for(wnid)
        urls = random.sample(urls, args.number)

        result = self.multidownload(urls, destination=args.output_dir, prefix=args.keyword)

        if args.verbosity == 1:
            print("Collected {} of {} images of {}".format(len(result), args.number, args.keyword))
        if args.verbosity > 1:
            print("\n".join(result))


if __name__ == "__main__":
    import argparse
    from imagyn.utils import IsRWDir

    Downloader().main()
