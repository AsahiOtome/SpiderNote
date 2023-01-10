import os
import re
import sys
import ddddocr

with open("./vcode.jpg", 'rb') as f:
    img = f.read()
orc = ddddocr.DdddOcr(show_ad=False)
res = orc.classification(img)
