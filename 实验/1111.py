import os
counts = 0
log_dir = 'C:/Users/Administrator/Desktop/暂存'
a = os.listdir(log_dir)
for i in a:
    file_path = f'{log_dir}/{i}'
    with open(file_path, 'r') as f:
        for line in f:
            if "ERROR" in line:
                counts += 1
print(counts)
#111111111


