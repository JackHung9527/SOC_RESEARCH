import zipfile, re, sys

z = zipfile.ZipFile(sys.argv[1])
ct = z.read('[Content_Types].xml').decode('utf-8')
themes = re.findall(r'theme[0-9]+', ct)
print('CT themes:', set(themes))
prels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
print('--- presentation.xml.rels theme entries ---')
for m in re.finditer(r'Target="[^"]*theme[^"]*"', prels):
    print(' ', m.group())
print()
nrels = z.read('ppt/notesMasters/_rels/notesMaster1.xml.rels').decode('utf-8')
print('--- notesMaster1.xml.rels ---')
print(nrels)
