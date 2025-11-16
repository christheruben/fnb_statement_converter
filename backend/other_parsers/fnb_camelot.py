import camelot


tables = camelot.read_pdf('./EASY_ACCOUNT_58.pdf', pages='1', flavor='lattice',)

print(camelot.plot(tables[0], kind='line').show())
input('Waiting...')