## Image Collection and Syntesis Microservice
Built for Echosec as part of the requirements of UVic SENG 499 Group Project

Imagyn (The python module in this repository) is a first implementation proof of concept framework for assembling training and testing datasets for building neural image recognizers.

The project is now over and this repository is less active, but feel free to fork and push back to this project.

Licensed for usage under the MIT Software Licensing agreement, and is free for usage so long as the usage is credited back to this repository.

### Learn
See [http://www.engr.uvic.ca/~zevisert/imagyn/](http://www.engr.uvic.ca/~zevisert/imagyn/)

## Install

    git clone https://github.com/blacklabai/Imagyn.git
    cd Imagyn
    python setup.py install
    
## Usage

### Find synsets and associated meta

    from imagyn.collection.lexicon import SynsetLexicon
    lexicon = SynsetLexicon()

    # Get a WordNet synset from keyword
    synset = lexicon.get_synset("car_battery")

    lexicon.get_parent(synset)
    lexicon.get_siblings(synset)
    lexicon.get_grandparents(synset)

    # Get the WordNet ID - for downloading images from ImageNet
    synset_id = lexicon.get_synset_id(synset)

    # Query ImageNet for the URLs of associated images
    urls = lexicon.API.urls_for(synset_id)
    
### Download images

    from imagyn.collection.download import Downloader

    num_images_per_synset = 10
    Downloader().download_multiple_synsets(count=num_images_per_synset, synsets=[synset], destination='temp', sequential=False)
    
## Creating a task pipeline with Luigi

Downloading batches of images is a potentially long-running task that interacts with multiple third-party services. Issues need to be handled and failures managed in a robust manner. [Luigi](https://github.com/spotify/luigi) can help with this by managing tasks. The `luigi/pipeline.py' script contains a pipeline and tasks that call Imagyn.

### Download a sample of images by exact match of a synset name to a key word:

    python pipeline.py DownloadImagesTask --local-scheduler --download-type Exact --keyword car_battery --num-images 10 --time 1
    
### Download images using the WordNet ID:
Set `num-images` to 0 to download all available images

    python pipeline.py DownloadSynsetTask  --local-scheduler --synset-id n02961225 --num-images 0
