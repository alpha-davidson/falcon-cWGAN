import tensorflow as tf
from tensorflow import keras
import numpy as np
import pandas as pd
import model
from datetime import date
from contextlib import redirect_stdout
import os

def main():
    print(tf.config.list_physical_devices())
    today = str(date.today())
    run_number = 0
    save_dir = '../models/Run_' + str(run_number) + '_' + today
    
    while (os.path.exists(save_dir)):
        run_number += 1
        save_dir = '../models/Run_' + str(run_number)  + '_' + today

    print("SAVE DIR: " + save_dir)
    os.makedirs(save_dir)
    assert(os.path.isdir(save_dir))
    
    net = model.make_model()
    fname = os.path.join(save_dir, 'modelsummary.txt')
    with open(fname, 'w') as f:
        with redirect_stdout(f):
            net.summary()

    data = np.loadtxt('../data/txt/matchData.txt', skiprows=2)
    partonMean = np.mean(data[:, :3], axis=0)
    partonStd = np.std(data[:, :3], axis=0)
    partonEMax = np.max(data[:, 3], axis=0)
    partonEMin = np.min(data[:, 3], axis=0)
    genMean = np.mean(data[:, 4:7], axis=0)
    genStd = np.std(data[:, 4:7], axis=0)
    genEMax = np.max(data[:, 7], axis=0)
    genEMin = np.min(data[:, 7], axis=0)

    data[:, :3] = (data[:, :3] - partonMean)/partonStd
    data[:, 3] = (data[:, 3] - partonEMin)/partonEMax
    data[:, 4:7] = (data[:, 4:7] - genMean)/genStd
    data[:, 7] = (data[:, 7] - genEMin)/genEMax
    '''
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)
    data = (data - mean)/std
    '''
    index = int(0.8*len(data))
    train = data[:index, :]
    trainParton = train[:, :4]
    trainGen = train[:, 4:]
    validate = data[index:, :]
    validateParton = validate[:, :4]
    validateGen = validate[:, 4:]
    
    checkpoint_path = os.path.join(save_dir, 'training/cp.cpkt')
    checkpoint_dir = os.path.dirname(checkpoint_path)

    cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
            save_weights_only=True,
            verbose=1,
            save_best_only=True)

    net.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-4),
           loss=keras.losses.MeanAbsoluteError(),
           metrics=[keras.metrics.MeanAbsoluteError()])

    history = net.fit(trainParton,
            trainGen,
            batch_size=64,
            epochs=50,
            validation_data=(validateParton, validateGen),
            callbacks=[cp_callback])

    loss = pd.Series(history.history['loss'])
    val_loss = pd.Series(history.history['val_loss'])

    loss_df = pd.DataFrame({'Training Loss': loss, 'Validation Loss': val_loss})
    fname = os.path.join(save_dir, 'losses.csv')
    loss_df.to_csv(fname)

    
if __name__ == "__main__":
    main()
