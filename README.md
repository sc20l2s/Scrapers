# Scrapers

### Installation / running:
When installing the project for the first time, run `setup.bat` <br>
Then to run the scrapers `launcher.bat` <br>
Everything else should be done for you.

### How it works:
These programs essentially automate navigating a webpage. 
A lot of newspaper archives have URLs that follow this structure (or something similair):
`https://www.lemonde.fr/archives-du-monde/{day}-{month}-{year}/{page}/`

The program works by looping through every possible date and page number in a selected year. Here's a simplified example:

`https://www.lemonde.fr/archives-du-monde/{19}-{11}-{2002}/{1}/` => Loop through every page in a given day (19th of November 2002) <br>
`https://www.lemonde.fr/archives-du-monde/{19}-{11}-{2002}/{2}/` <br>
`https://www.lemonde.fr/archives-du-monde/{19}-{11}-{2002}/{3}/` <br>
`...` <br>
`https://www.lemonde.fr/archives-du-monde/{20}-{11}-{2002}/{1}/` => Once we are done move onto the next day and continue <br>

Eventually, it goes through **every page of every day** in the year you've chosen.

The program runs slowly on purpose so it doesn’t overwhelm the newspaper’s website with requests.

At each page it visits, the program:
1. Temporarily downloads the webpage code (called HTML).
2. Scans it for article titles that contain specific **keywords** (you choose these when you run it).
3. If it finds a match, it saves the article title and link in a `.txt` file.

The final result is a text file that contains all matching articles found during the search. You can open this file in any text editor.
