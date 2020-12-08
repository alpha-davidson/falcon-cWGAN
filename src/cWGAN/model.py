import tensorflow as tf
from tensorflow import keras
import numpy as np
from tensorflow.keras.constraints import max_norm


class weight_clipping(tf.keras.constraints.Constraint):
    '''
    TODO: implement as way of clipping weights in network
    '''

    def __init__(self, ref_value):
        self.ref_value = ref_value



class cWGAN():
    def __init__(self, num_critic_iters, batch_size, noise_dims=4):
        # hyper parameters recommended by paper
        self.num_critic_iters = num_critic_iters
        self.clip_value = 0.01
        self.critic_optimizer = tf.keras.optimizers.RMSprop(lr=5e-5)
        self.generator_optimizer = tf.keras.optimizers.RMSprop(lr=5e-5)
        self.batch_size = batch_size 


        self.noise_dims = noise_dims
        self.generator = self.build_generator()
        self.critic = self.build_critic()

    def build_generator(self):
        noise = keras.Input(shape=(self.noise_dims,), name="noiseIn")
        pJet = keras.Input(shape=(4,), name="pjetIn")

        
        x = keras.layers.Dense(32, activation='relu', name="genx1")(pJet)
        x = keras.layers.Dense(64, activation='relu', name="genx2")(x)
        x = keras.layers.Dense(64, activation='relu', name="genx3")(x)

        y = keras.layers.Dense(32, activation='relu', name="geny1")(noise)
        y = keras.layers.Dense(64, activation='relu', name="geny2")(y)
        y = keras.layers.Dense(64, activation='relu', name="geny3")(y)

        concat = keras.layers.concatenate([x, y], name="concat")
        out = keras.layers.Dense(64, activation='relu', name="both1")(concat)
        out = keras.layers.Dense(64, activation='relu', name="both2")(concat)
        out = keras.layers.Dense(4, name="out")(out)
        return keras.Model([pJet, noise], out)
   

    def build_critic(self):
        pJet = keras.Input(shape=(4,))
        rJet = keras.Input(shape=(4,))

        x = keras.layers.Dense(32, activation='relu')(pJet)
        x = keras.layers.Dense(64, activation='relu')(x)
        x = keras.layers.Dense(64, activation='relu')(x)

        y = keras.layers.Dense(32, activation='relu')(rJet)
        y = keras.layers.Dense(64, activation='relu')(y)
        y = keras.layers.Dense(64, activation='relu')(y)

        concat = keras.layers.concatenate([x, y])
        out = keras.layers.Dense(128, activation='relu')(concat)
        out = keras.layers.Dense(128, activation='relu')(concat)
        out = keras.layers.Dense(1)(out)
        return keras.Model([pJet, rJet], out)


    def print_network(self):
        self.generator.summary()
        self.critic.summary()


    #@tf.function
    def critic_loss(self, real_output, fake_output):
        '''
        The negative of the estimate of the wasserstein distance (negative
        because we want to perform gradient ascent on the critic)
        '''
        loss = -(tf.math.reduce_mean(real_output) -
                tf.math.reduce_mean(fake_output))
        #print("Critic loss: {}".format(loss))
        return loss


    #@tf.function
    def generator_loss(self, fake_output):
        loss = -tf.math.reduce_mean(fake_output)
        #print("Gen Loss: {}".format(loss.numpy()))
        return loss

         
    #@tf.function
    def clip_critic_weights(self):
        for l in self.critic.layers:
            new_weights = []
            for i in range(len(l.weights)):
                new_weights.append(tf.clip_by_value(l.weights[i],
                    -self.clip_value, self.clip_value))
            l.set_weights(new_weights)
                

    #@tf.function
    def train_critic(self, pJets, rJets):
        noise = tf.random.uniform((tf.shape(pJets)[0], self.noise_dims), 0, 1, tf.float32)
        with tf.GradientTape(persistent=True) as tape:
            generated_rJets = self.generator([pJets, noise],
                    training=False)
            real_output = self.critic([pJets, rJets], training=True)
            fake_output = self.critic([pJets, generated_rJets],
                    training=True)

            critic_loss_val = self.critic_loss(real_output, fake_output)
        
        #print("    Critic Loss: {}".format(critic_loss))
        critic_grads = tape.gradient(critic_loss_val,
                self.critic.trainable_variables)

        self.critic_optimizer.apply_gradients(zip(critic_grads,
            self.critic.trainable_variables))

        self.clip_critic_weights()

        return critic_loss_val


    #@tf.function
    def train_generator(self, pJets):
        noise = tf.random.uniform((tf.shape(pJets)[0], self.noise_dims), 0, 1, tf.float32)

        with tf.GradientTape() as tape:
            generated_rJets = self.generator([pJets, noise], training=True)
            fake_output = self.critic([pJets, generated_rJets], training=False)
            generator_loss_val = self.generator_loss(fake_output)

        generator_grads = tape.gradient(generator_loss_val,
                self.generator.trainable_variables)
        self.generator_optimizer.apply_gradients(zip(generator_grads,
            self.generator.trainable_variables))


    #@tf.function
    def train_step(self, data):
        count = 0
        wass_estimate = 0.0
        critic_losses = []
        for batch in data:
            if count < self.num_critic_iters:
                critic_loss_val = self.train_critic(batch[0], batch[1])
                critic_losses.append(critic_loss_val)
            if count == self.num_critic_iters:
                self.train_generator(batch[0])
            if count == self.num_critic_iters + 1:
                pJets = batch[0]
                rJets = batch[1]
                noise = tf.random.uniform((tf.shape(pJets)[0], self.noise_dims), 0, 1, tf.float32)

                generated_rJets = self.generator([pJets, noise], training=False)
                real_output = self.critic([pJets, rJets], training=False)
                fake_output = self.critic([pJets, generated_rJets], training=False)
                wass_estimate = -self.critic_loss(real_output, fake_output)
            count += 1

        return wass_estimate, critic_losses


class cWGAN_mnist(cWGAN):

    def build_generator(self): 
        noise = keras.Input(shape=(self.noise_dims,))
        number_input = keras.Input(shape=(10,))

        x = keras.layers.Dense(10, activation='relu')(number_input)
        x = keras.layers.Dense(32, activation='relu')(x)
        
        y = keras.layers.Dense(self.noise_dims, activation='relu')(noise)
        y = keras.layers.Dense(self.noise_dims, activation='relu')(y)

        concat = keras.layers.concatenate([x, y])
        out = keras.layers.Dense(7*7*256, activation='relu')(concat)
        
        out = keras.layers.Reshape((7, 7, 256))(out)
        out = keras.layers.Conv2DTranspose(128, (5, 5), strides=(1, 1),
                padding='same', use_bias=False)(out)
        out = keras.layers.LeakyReLU()(out)
        out = keras.layers.Conv2DTranspose(64, (5, 5), strides=(2, 2),
                padding='same', use_bias=False)(out)
        out = keras.layers.LeakyReLU()(out)
        out = keras.layers.Conv2DTranspose(1, (5, 5), strides=(2, 2),
                padding='same', use_bias=False, activation='tanh')(out)

        
        return keras.Model([number_input, noise], out)

    def build_critic(self):
        number_input = keras.Input(shape=(10,))
        image = keras.Input(shape=(28, 28, 1))

        x = keras.layers.Dense(10, activation='relu')(number_input)

        y = keras.layers.Conv2D(64, (5, 5), strides=(2, 2),
                padding='same')(image)
        y = keras.layers.LeakyReLU()(y)
        y = keras.layers.Conv2D(128, (5, 5), strides=(2, 2), padding='same')(y)
        y = keras.layers.LeakyReLU()(y)
        y = keras.layers.Conv2D(128, (5, 5), strides=(2, 2), padding='same')(y)
        y = keras.layers.LeakyReLU()(y)

        y = keras.layers.Flatten()(y)

        concat = keras.layers.concatenate([x, y])
        out = keras.layers.Dense(100)(concat)
        out = keras.layers.Dense(100)(out)
        out = keras.layers.Dense(50)(out)
        out = keras.layers.Dense(1)(out)

        return keras.Model([number_input, image], out)



def main():

    net = cWGAN_mnist(5, 64, 100)
    net.print_network()


if __name__ == "__main__":
    main()