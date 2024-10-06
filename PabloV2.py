from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
import copy

current_directory = os.getcwd()
python_directory = current_directory.split('\PabloV2')[0]

import random # used for randomly selecting NFT image layers and traits
import pandas as pd # used for creating spreadsheet of NFT traits, IDs, names and images
from pathlib import Path # used for importing other modules


sys.path.insert(1, python_directory + '/CSV Converter')
from CSVConverter import CSVConverter
sys.path.insert(1, python_directory + '/ImageTools')
from ImageTools import ImageTools




class Pablo:
    def __init__(self, config):
        self.silent_mode = True
        self.CSV = CSVConverter()
        self.IMG = ImageTools()
        self.loadCollection(config)


    def loadCollection(self, config):
        self.config = config
        self.collection = config['collection']
        self.traits = config['traits']
        self.settings = config['settings']

        self.width = self.config['settings']['image_width']
        self.height = self.config['settings']['image_height']

        # Create new folders if they don't exist
        self.image_asset_folder = current_directory + '/collections/' + self.collection['sname'] + '/' + self.settings['image_asset_folder'] + '/'
        if not(os.path.isdir(self.image_asset_folder)):
            os.mkdir(self.image_asset_folder)
        self.image_output_folder = current_directory + '/collections/' + self.collection['sname'] + '/' +  self.settings['image_output_folder'] + '/'
        if not(os.path.isdir(self.image_output_folder)):
            os.mkdir(self.image_output_folder)
        self.metadata_output_folder = current_directory + '/collections/' + self.collection['sname'] + '/' +  self.settings['metadata_output_folder'] + '/'
        if not(os.path.isdir(self.metadata_output_folder)):
            os.mkdir(self.metadata_output_folder)

        
        # Set an RNG seed to make the generation reproducible
        if self.settings.get('seed'):
            random.seed(self.settings['seed'])

        # Calculate rarities of the different traits
        self.trait_rarities = self.generateTraitRarities()


    def generateTraitRarities(self):
        trait_rarities = {}
        # iterate through different trait types
        for trait_type in os.listdir(self.image_asset_folder):
            # collect probabilities from config
            trait_type_rarities = {}
            num_unassigned_rarities = 0
            amount_rarity_assigned = 0
            for trait_value in os.listdir(self.image_asset_folder + '/' + trait_type):
                trait_value = trait_value.split('.')[0]
                trait_value_rarity = 0
                if self.traits.get(trait_type):
                    if self.traits[trait_type].get('values'):
                        if self.traits[trait_type]['values'].get(trait_value):
                            trait_value_rarity = self.traits[trait_type]['values'][trait_value]
                trait_type_rarities[trait_value] = trait_value_rarity
                if trait_value_rarity == 0:
                    num_unassigned_rarities += 1
                else:
                    amount_rarity_assigned += trait_value_rarity
            # fill in missing probabilities 
            for trait_value in trait_type_rarities:
                if trait_type_rarities[trait_value] == 0:
                    trait_type_rarities[trait_value] = (1 - amount_rarity_assigned) / num_unassigned_rarities
            trait_rarities[trait_type] = trait_type_rarities
            
        self.trait_rarities = trait_rarities
        if not(self.silent_mode):
            print(trait_rarities)
        return(trait_rarities)
        



    def generate(self, token_ID=1, name=None):
        if not(name):
            name = self.collection['name'] + ' #' + str(token_ID)
        new_NFT_dict = {'ID': token_ID,
                        'Name': name,
                        'Image': '',
                        'Image URI': '',
                        'Traits': {},
                        'JSON Contents': [],
                        'JSON URI': '',
                        'Z-index Dict': {}}

        if not(self.trait_rarities):
            self.trait_rarities = self.generateTraitRarities()

        # create new random trait combination
        new_NFT_dict = self.generateNewTraits(new_NFT_dict)

        # create image using selected traits
        new_NFT_dict = self.generateNewImage(new_NFT_dict)

        # create JSON file with selected traits
        new_NFT_dict = self.generateTraitFile(new_NFT_dict)

        if not(self.silent_mode):
            print(new_NFT_dict)

        return(new_NFT_dict)

        


    def generateNewTraits(self, NFT_dict):
        # select traits at random
        # TO ADD: while loop to guarantee uniquess based on minimum_unique_traits in config "Settings"
        for trait_type in self.trait_rarities:
            random_number = random.random()
            z_index = 0
            # checks if the trait type has a particular layering (which is common)
            if self.traits[trait_type].get('z-index'):
                z_index = self.traits[trait_type]['z-index']
            accumulated_rarity = 0
            for trait_value in self.trait_rarities[trait_type]:
                rarity = self.trait_rarities[trait_type][trait_value]
                if (random_number >= accumulated_rarity) and (random_number < accumulated_rarity + rarity):
                    trait_image_location = self.image_asset_folder + '/' + trait_type + '/' + trait_value + '.' + self.settings['image_file_type']
                    # checks if the trait value has a paticular layering (which is uncommon)
                    if self.traits[trait_type].get('values'):
                        if self.traits[trait_type]['values'].get(trait_value):
                            if self.traits[trait_type]['values'][trait_value].get('z-index'):
                                z_index = self.traits[trait_type]['values'][trait_value]['z-index']
                    NFT_dict['Traits'][trait_type] = {'Value': trait_value,
                                                      'Z-index': z_index,
                                                      'Image Location': trait_image_location,
                                                      'Rarity': rarity}
                    # sets a unique z-index for the trait
                    while NFT_dict['Z-index Dict'].get(z_index):
                        z_index += 1
                    NFT_dict['Z-index Dict'][z_index] = trait_type
                accumulated_rarity += rarity

        return(NFT_dict)


    def generateNewImage(self, NFT_dict):
        # create NFT image
        new_NFT_image = self.IMG.createBlankImage(self.width, self.height)
        z_index_dict = copy.deepcopy(NFT_dict['Z-index Dict'])
        while z_index_dict:
            lowest_z_index = min(z_index_dict)
            trait_type = z_index_dict[lowest_z_index]
            trait_image_location = NFT_dict['Traits'][trait_type]['Image Location']
            new_NFT_image = self.IMG.overlay(base_image=new_NFT_image, added_image_name=trait_image_location, save_image=False)

            del z_index_dict[lowest_z_index]

        NFT_dict['Image'] = new_NFT_image
        self.IMG.saveImage(new_NFT_image, self.image_output_folder, str(NFT_dict['ID']) + '.png')
        return(NFT_dict) 



    def generateTraitFile(self, NFT_dict):
        new_trait_file = open(self.metadata_output_folder + str(NFT_dict['ID']) + '.json', 'w')
        NFT_dict = self.initializeJSONcontents(NFT_dict)
        # create NFT trait JSON file contents
        trait_count = 0
        for trait_type in NFT_dict['Traits']:
            trait_count+=1
            if trait_count == len(NFT_dict['Traits']):
                NFT_dict = self.addTraitToJSONcontents(NFT_dict, trait_type, last_trait=True)
            else:
                NFT_dict = self.addTraitToJSONcontents(NFT_dict, trait_type)
        for line in NFT_dict['JSON Contents']:
            new_trait_file.write(line + '\n')
        new_trait_file.close()
        return(NFT_dict)


    def initializeJSONcontents(self, NFT_dict):
        # description of NFT
        if NFT_dict.get('Description'):
            description = NFT_dict['Description']
        else:
            description = 'description'
            
        # image URI of NFT
        if NFT_dict.get('Image URI'):
            image_URI = NFT_dict['Image URI']
        else:
            image_URI = 'image_URI'
            
        # name of NFT
        if NFT_dict.get('Name'):
            name = NFT_dict['Name']
        elif self.collection.get('name') and NFT_dict.get('ID'):
            name = self.collection['name'] + ' #' + str(NFT_dict['ID'])
        elif NFT_dict.get('ID'):
            name = str(NFT_dict['ID'])
        else:
            name = 'name'
                
        NFT_dict['JSON Contents'] = []
        NFT_dict['JSON Contents'].append('{')
        NFT_dict['JSON Contents'].append('    "description": "' + description + '",')
        NFT_dict['JSON Contents'].append('    "image": "' + image_URI + '",')
        NFT_dict['JSON Contents'].append('    "name": "' + name + '",')
        NFT_dict['JSON Contents'].append('    "attributes": [')
        return(NFT_dict)


    def addTraitToJSONcontents(self, NFT_dict, trait_type, last_trait=False):
        NFT_dict['JSON Contents'].append('        {')
        NFT_dict['JSON Contents'].append('              "trait_type": "' + trait_type + '",')
        NFT_dict['JSON Contents'].append('              "value": "' + NFT_dict['Traits'][trait_type]['Value'] + '"')
        if last_trait:
            NFT_dict['JSON Contents'].append('        }]}')
        else:
            NFT_dict['JSON Contents'].append('        },')
        return(NFT_dict)
            

                        

    def generateCollection(self, collection_size=10, name_prefix=None, generation_method='PIL'):
        new_NFT_collection = {}
        
        # Set collection size
        if not(collection_size):
            collection_size = self.collection.get('collection_size')
        if not(collection_size):
            collection_size = int(input('\nHow many images would you like to generate?\nCollection Size: '))

        # Iterate through token IDs to generate images
        self.NFTs_by_ID = {}
        initial_index = self.settings['initial_index']
        for token_ID in range(initial_index, collection_size + initial_index):
            if name_prefix:
                name = name_prefix + ' ' + str(token_ID)
            else:
                name = None
            new_NFT_dict = self.generate(token_ID, name=name)
            new_NFT_collection[token_ID] = new_NFT_dict

        if not(self.silent_mode):
            print(new_NFT_collection)
        
        # use Pandas to create a spreadsheet of every possible trait combination and its probability
##        potential_collection_stast = [{'Some List': 'of Dicts'}]

        # use Pandas to create a spreadsheet of each NFT in order of ID and its trait rarity
##        actual_collection_stats = [{'Some List': 'of Dicts'}]

        # generate contract metadata
        #### Old
        #P.writeCollectionFile()
        #P.writeContractFile()
        #P.writeSettingsFile()

    def cloneJSON(self, quantity, JSON_file_name='X.json', replace_marker='%%%'):
        original_JSON_file = open(JSON_file_name, 'r')
        JSON_file_contents = list(original_JSON_file)
        original_JSON_file.close()
        for num in range(quantity):
            print(num)
            new_JSON_file = open('json_clones/' + str(num + 1) + '.json', 'w')
            for line in JSON_file_contents:
                if not(self.silent_mode):
                    print(line)
                if replace_marker in line:
                    line = line.split(replace_marker)[0] + str(num + 1) + line.split(replace_marker)[1]
                    if not(self.silent_mode):
                        print(line)
                new_JSON_file.write(line)
            new_JSON_file.close()
        

if __name__ == '__main__':
    config = json.load(open('collections/aphid_1.json'))
    P = Pablo(config)
    P.silent_mode = True
    #P.generate()
    P.generateCollection(50)
    #P.cloneJSON(100)
    
    
        
