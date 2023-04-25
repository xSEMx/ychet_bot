def test(text):
    return int(text.split()[1])
try:
    text_1 = '/link_parent 4r4rr'

    print(test(text_1))
except Exception as e:
    print(e.__class__)

    if isinstance(e, ValueError):
        print(True)


