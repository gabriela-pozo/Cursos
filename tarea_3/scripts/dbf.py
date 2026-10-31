import struct, sys
def read_dbf(path, nrows=None, enc='latin-1'):
    with open(path,'rb') as f:
        h=f.read(32)
        n=struct.unpack('<I',h[4:8])[0]; hl,rl=struct.unpack('<HH',h[8:12])
        fields=[]
        while True:
            d=f.read(32)
            if d[0]==0x0D: break
            fields.append((d[:11].split(b'\0')[0].decode(),chr(d[11]),d[16],d[17]))
        f.seek(hl)
        rows=[]
        for i in range(n if nrows is None else min(nrows,n)):
            r=f.read(rl); pos=1; row={}
            for name,t,l,dc in fields:
                row[name]=r[pos:pos+l].decode(enc).strip(); pos+=l
            rows.append(row)
    return n,fields,rows
if __name__=='__main__':
    n,fields,rows=read_dbf(sys.argv[1],2)
    print(sys.argv[1],'filas',n); print([ (a,b,c) for a,b,c,d in fields])
    for r in rows: print(r)
