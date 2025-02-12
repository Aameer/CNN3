from keras.layers import Dense, Flatten
from keras.models import Sequential
from keras.callbacks import Callback
from keras.applications.vgg16 import VGG16, preprocess_input
from keras.optimizers import SGD, RMSprop
import pandas as pd
import numpy as np
import cv2
from PIL import Image
import keras
import subprocess
import os

import wandb
from wandb.keras import WandbCallback

run = wandb.init()
config = run.config

config.batch_size = 32
config.num_epochs = 20

input_shape = (48, 48, 1)

def load_fer2013():
    if not os.path.exists("fer2013"):
        print("Downloading the face emotion dataset...")
        subprocess.check_output("wget -SL https://www.dropbox.com/s/opuvvdv3uligypx/fer2013.tar | tar fxvz", shell=True)
    data = pd.read_csv("fer2013/fer2013.csv")
    pixels = data['pixels'].tolist()
    width, height = 48, 48
    faces = []
    for pixel_sequence in pixels:
        face = np.asarray(pixel_sequence.split(' '), dtype=np.uint8).reshape(width, height) # reshape isnt working?
        face = cv2.resize(face.astype('uint8'), (width, height))
        faces.append(face.astype('float32'))

    faces = np.asarray(faces)
    oldfaces =  np.expand_dims(faces, -1)
    #faces= np.array(faces.ravel()).reshape(48,48,3)
    #faces = faces[:, :, None] * np.ones(3, dtype=int)[None, None, :]
    faces = np.stack((faces,)*3, axis=-1)
    
    #import pdb;pdb.set_trace()
    #faces = np.expand_dims(faces, -3)
    #os.sys.exit(0)
    emotions = pd.get_dummies(data['emotion']).as_matrix()
    
    val_faces = faces[int(len(faces) * 0.8):]
    val_emotions = emotions[int(len(faces) * 0.8):]
    train_faces = faces[:int(len(faces) * 0.8)]
    train_emotions = emotions[:int(len(faces) * 0.8)]
    
    return train_faces, train_emotions, val_faces, val_emotions

# loading dataset

train_faces, train_emotions, val_faces, val_emotions = load_fer2013()
#import pdb;pdb.set_trace()
num_samples, num_classes = train_emotions.shape

train_faces /= 255.
val_faces /= 255.


# setup model
conv_base = VGG16(include_top=False, weights='imagenet', input_shape=(48, 48, 3))

model = Sequential()

model.add(conv_base)
model.add(Flatten(input_shape=conv_base.output_shape[1:]))
model.add(Dense(256, activation='relu'))
model.add(Dense(7, activation='sigmoid'))

conv_base.trainable = False

set_trainable = False
for layer in conv_base.layers:
    print(">>", layer.name,layer.trainable)
    if layer.name == 'block5_conv1':
        set_trainable = True
    if set_trainable:
        layer.trainable = True
        #set_trainable=False
    else:
        layer.trainable = False
    print("OUT", layer.name,layer.trainable)

    # transfer learning
model.compile(loss='binary_crossentropy',
              optimizer=RMSprop(lr=1e-5),
              metrics=['acc'])


#model.add(Flatten(input_shape=input_shape))
#model.add(Dense(num_classes, activation="softmax"))

#model.compile(optimizer='adam', loss='categorical_crossentropy',metrics=['accuracy'])

model.fit(train_faces, train_emotions, batch_size=config.batch_size,
        epochs=config.num_epochs, verbose=1, callbacks=[
            WandbCallback(data_type="image", labels=["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"])
        ], validation_data=(val_faces, val_emotions))


model.save("emotion.h5")



