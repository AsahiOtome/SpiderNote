from util import *
import numpy as np

df = pd.read_excel('input_df.xlsx')
refer = pd.read_excel('input_refer.xlsx')
output = pd.DataFrame(np.zeros((2000, 28)))
output.columns = df.columns
output['角色名称'] = None
output['个人特技'] = None
output['特技说明'] = None

j = 0
k = 0
for i in range(2000):
    if j >= len(df):
        j = 0
        k += 1
    if k >= len(refer):
        break
    if j in range(20):
        if df.loc[j, '备注'].find(refer.loc[k, '角色名称']) >= 0:
            pass
        else:
            for _ in range(j, 21):
                j = _
                if str(df.loc[_, '备注']).find(refer.loc[k, '角色名称']) >= 0:
                    break
    for col in output:
        if col in df.columns and col not in refer.columns:
            output.loc[i, col] = df.loc[j, col]
        elif col in df.columns and col in refer.columns:
            output.loc[i, col] = df.loc[j, col] + refer.loc[k, col]
        else:
            output.loc[i, col] = refer.loc[k, col]
    j += 1
