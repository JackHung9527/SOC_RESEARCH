import zipfile, re, sys
z = zipfile.ZipFile(sys.argv[1] if len(sys.argv) > 1 else r'DOC\會議紀錄\meeting_0506_洪大甲.pptx')
for name in z.namelist():
    if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
        xml = z.read(name).decode('utf-8')
        for m in re.finditer(r'<a:ext\s+cx="(-?\d+)"\s+cy="(-?\d+)"', xml):
            cx, cy = int(m.group(1)), int(m.group(2))
            if cx < 0 or cy < 0:
                print(f'{name}: NEG cx={cx}, cy={cy}')
        for m in re.finditer(r'<a:off\s+x="(-?\d+)"\s+y="(-?\d+)"', xml):
            x, y = int(m.group(1)), int(m.group(2))
            if x < 0 or y < 0:
                print(f'{name}: NEG off x={x}, y={y}')
