"""
A spectrogram, or sonogram, is a visual representation of the spectrum
of frequencies in a sound.  Horizontal axis represents time, Vertical axis
represents frequency, and color represents amplitude.


remove blank border arount pyplot:
http://stackoverflow.com/questions/11837979/removing-white-space-around-a-saved-image-in-matplotlib


"""

import sys
import os
import wave
import matplotlib
matplotlib.use('Agg')
import pylab
import subprocess


def graph_spectrogram(media_file, chunk_size):

    fileName1stChunk = ''

    wav_file = extract_wav(media_file)
    if not wav_file:
        return None

    sound_info, frame_rate = get_wav_info(wav_file)

    wav_length = round(len(sound_info) / frame_rate, 0)
    print('wav tot length', wav_length)
    if wav_length < chunk_size:
        chunk_size = round(wav_length)

    i = 0
    while True:

        chunkFileName = "{}.{}-{}.spectrogram.png".format(wav_file, i, i + chunk_size)
        if not os.path.isfile(chunkFileName):

            sound_info_slice = sound_info[i * frame_rate: (i + chunk_size) * frame_rate]

            #print( [i * frame_rate, (i + chunk_size) * frame_rate] )

            pylab.figure(num=None, dpi=100, figsize=(int( len(sound_info_slice)/frame_rate  ), 1))
            pylab.gca().set_axis_off()
            pylab.margins(0, 0)
            pylab.gca().xaxis.set_major_locator(pylab.NullLocator())
            pylab.gca().yaxis.set_major_locator(pylab.NullLocator())
            pylab.specgram(sound_info_slice, Fs=frame_rate, cmap=matplotlib.pyplot.get_cmap('Greys'))
            pylab.savefig(chunkFileName,  bbox_inches='tight', pad_inches=0)

            print(chunkFileName + ' created')

            pylab.clf()
            pylab.close()
        else:
            print(chunkFileName + ' already exists')


        if not fileName1stChunk:
            fileName1stChunk = chunkFileName

        i += chunk_size
        if i >= wav_length:
            break

    return fileName1stChunk


def extract_wav(mediaFile):
    '''extract wav from media file'''

    if os.path.isfile(mediaFile + '.wav'):
        return mediaFile + '.wav'
    else:
        p = subprocess.Popen( 'ffmpeg -i "{0}" -y -ac 1 -vn "{0}.wav"'.format(mediaFile), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
        out, error = p.communicate()
        out, error = out.decode('utf-8'), error.decode('utf-8')

        if not out:
            return mediaFile + '.wav'
        else:
            return None


def get_wav_info(wav_file):

    wav = wave.open(wav_file, 'r')
    frames = wav.readframes(-1)
    sound_info = pylab.fromstring(frames, 'Int16')
    frame_rate = wav.getframerate()
    wav.close()
    return sound_info, frame_rate


if __name__ == '__main__':
    media_file = sys.argv[1]
    graph_spectrogram(media_file, 20)
