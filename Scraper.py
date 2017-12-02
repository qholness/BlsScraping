#!/usr/bin/python3
"""
Main intent is to scrape BLS information from the Occupational Handbook
"""
from bs4 import BeautifulSoup as Tasty
import requests as pyrequests
import pandas as pd
import tqdm
import sys
import os



class BlsScraper:
    bls_url = "https://www.bls.gov"
    links_exist = False
    bls_occupation_links = set()
    data = None

    def generate_occupation_group_link(self, insert):
        """Generate occupation group link"""
        if insert.get('href'):
            path = "{}{}".format(self.bls_url, insert['href'])
            path = path.lstrip().rstrip().replace("tab-4", "")
            return path
        return None


    def generate_occupation_pages(self):
        response = pyrequests.get("{}/ooh/".format(self.bls_url))
        html = response.text
        soup = Tasty(html, 'html.parser')
        ooh_occupation_list = soup.find(id="ooh-occupation-list")
        a_tags = ooh_occupation_list.find_all('a')
        links = map(self.generate_occupation_group_link, a_tags)

        return links
    
    def export_links(self, outfile="links.txt", overwrite=True):
        newSoup = None
        bls_occupation_links = set()

        if not os.path.exists(outfile) or overwrite==True:
            iterable = tqdm.tqdm(self.generate_occupation_pages(), desc="fetching occ urls")
            for o in iterable:
                try:
                    response = pyrequests.get(o)
                except pyrequests.exceptions.ConnectionError:
                    print("Error connecting to %s, skipping" % o)
                    continue
                newSoup = Tasty(response.text, 'html.parser')
                occs = newSoup.find(id="landing-page-table")

                if occs:
                    occ_as = occs.find_all('a')
                    for _ in occ_as:
                        bls_occupation_links.add(self.generate_occupation_group_link(_))

            with open(outfile, "w+") as links:
                # Write out links
                for l in bls_occupation_links:
                    links.write(l)
                    links.write("\n")
        setattr(self, 'bls_occupation_links', list(bls_occupation_links) )
        return self

    def grab_data(self):
        if self.bls_occupation_links:
            
            def edit_title(title):
                if hasattr(title, 'string'):
                    title = title\
                        .string\
                        .replace("<h1>","")\
                        .replace("</h1>", "")\
                        .lstrip()\
                        .rstrip()
                    title = title[:-1] if title[-1] == "s" else title # Truncate title's s to singular
                    return title
                return title


            def edit_description(p_tags):
                desc = p_tags.pop(0).string.replace("<p>","").replace("</p>", "").lstrip().rstrip()
                    
                if "Please enable javascript" in desc:
                    desc = p_tags\
                            .pop(0)\
                            .string\
                            .replace("<p>","")\
                            .replace("</p>", "")\
                            .lstrip()\
                            .rstrip()
                return desc
            gen_nones = lambda : [None for n in range(len(self.bls_occupation_links))]
            categoryids, titles, descriptions, urls = gen_nones(), gen_nones(), gen_nones(), gen_nones()
            
            tqdm_iter = tqdm.tqdm(self.bls_occupation_links, desc="grabbing data")
            iterable = enumerate(tqdm_iter)    

            for idx, occupation_url in iterable:
                occupation_url = occupation_url.replace("\n", "")
                try:
                    response = pyrequests.get(occupation_url)
                except pyrequests.exceptions.ConnectionError:
                    print("Error connecting to %s, skipping" % occupation_url)
                    continue                
                html = Tasty(response.text, 'html.parser')
                
                try:
                    title = html.find_all('h1')[0] # Assuming the first h1 tag is the title may be bad... Mkay?
                except IndexError:
                    print("Unable to grab header, skipping %s" % occupation_url)
                    continue
                p_tags = html.find_all('p')

                try:
                    title = edit_title(title)
                    try:
                        description = edit_description(p_tags)
                        descriptions[idx] = description
                    except AttributeError:
                        print("Attribute missing, skipping description for %s" % occupation_url)

                    titles[idx] = title
                    urls[idx] = occupation_url
                    categoryids[idx] = idx
                except:
                    print("Failed: {}".format(sys.exc_info()), idx)
            
            data = pd.DataFrame({"title" : titles, "description" : descriptions
                ,"categoryid" : categoryids, "bls_url" : urls})
            setattr(self, 'data', data)

            return self

    def export_data(self, outpath="bls_data.csv", *args, **kwargs):
        if isinstance(self.data, pd.DataFrame):
            if not self.data.empty:
                self.data.to_csv(outpath, *args, **kwargs)

    
    def run(self):
        self.export_links()
        self.grab_data()
        self.export_data()
