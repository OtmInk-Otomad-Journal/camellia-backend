import pydub
import numpy as np
aid = 488668323
start_time = 2000
duration = 10000
sound = pydub.AudioSegment.from_file(f"./video/{aid}.mp4")
# sound = pydub.AudioSegment.from_file(f"./audio/959364866.mp3")
silent_time = 500
silent = pydub.AudioSegment.silent(duration=silent_time)
sound = sound[start_time:start_time+duration] # 切片

sound = sound.apply_gain(-sound.max_dBFS) # 响度标准化

# 判断分组极差，判断压缩
chunks = pydub.utils.make_chunks(sound,100)
dBFS_array = []
for i, chunk in enumerate(chunks):
    dBFS_array.append(chunk.max_dBFS)
dBFS_aver = np.average(dBFS_array)
if(abs(np.max(dBFS_array) - dBFS_aver)) > 2.5: # 若偏差大于 2.5，则压缩
    sound = sound.apply_gain(-dBFS_aver)
    sound = pydub.effects.compress_dynamic_range(sound,threshold=0,ratio=4.0, attack=5.0, release=50.0)

sound = silent.append(sound,crossfade = silent_time)
sound = sound.append(silent,crossfade = silent_time) # 交叉淡入
sound.export(f"./audio/{aid}.mp3",
            format="mp3",
            bitrate="320k")