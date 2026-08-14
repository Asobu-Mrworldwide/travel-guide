import json
d=json.load(open('indonesia/indonesia.json',encoding='utf-8'))
out=[]
for i,sec in enumerate(d['spot_sections']):
    out.append(str(i)+' '+json.dumps({k:v for k,v in sec.items() if k!='spots'}, ensure_ascii=False))
out.append('')
out.append(json.dumps(d['spot_sections'][0]['spots'][0], ensure_ascii=False, indent=2))
out.append(json.dumps(d.get('spots_filter_cities'), ensure_ascii=False))
out.append(json.dumps(d.get('spots_filter_types'), ensure_ascii=False))
open('scratch_out4.txt','w',encoding='utf-8').write(chr(10).join(out))
