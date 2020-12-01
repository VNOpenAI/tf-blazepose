import tensorflow as tf
from tensorflow.keras.models import Model
from ...model_type import ModelType
from .blazepose_layers import BlazeBlock


class BlazePose():
    def __init__(self, num_joints: int, model_type: ModelType = ModelType.REGRESSION):

        self.model_type = model_type
        self.num_joints = num_joints
        self.conv1 = tf.keras.layers.Conv2D(
            filters=24, kernel_size=3, strides=(2, 2), padding='same', activation='relu'
        )

        self.conv2_1 = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding='same', activation=None),
            tf.keras.layers.Conv2D(filters=24, kernel_size=1, activation=None)
        ])

        self.conv2_2 = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding='same', activation=None),
            tf.keras.layers.Conv2D(filters=24, kernel_size=1, activation=None)
        ])

        # === Heatmap ===

        self.conv3 = BlazeBlock(block_num=3, channel=48)    # input res: 128
        self.conv4 = BlazeBlock(block_num=4, channel=96)    # input res: 64
        self.conv5 = BlazeBlock(block_num=5, channel=192)   # input res: 32
        self.conv6 = BlazeBlock(block_num=6, channel=288)   # input res: 16

        self.conv7a = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=48, kernel_size=1, activation="relu"),
            tf.keras.layers.UpSampling2D(size=(2, 2), interpolation="bilinear")
        ])
        self.conv7b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=48, kernel_size=1, activation="relu")
        ])

        self.conv8a = tf.keras.layers.UpSampling2D(
            size=(2, 2), interpolation="bilinear")
        self.conv8b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=48, kernel_size=1, activation="relu")
        ])

        self.conv9a = tf.keras.layers.UpSampling2D(
            size=(2, 2), interpolation="bilinear")
        self.conv9b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=48, kernel_size=1, activation="relu")
        ])

        self.conv10a = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=8, kernel_size=1, activation="relu"),
            tf.keras.layers.UpSampling2D(size=(2, 2), interpolation="bilinear")
        ])
        self.conv10b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(filters=8, kernel_size=1, activation="relu")
        ])

        self.conv11 = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=8, kernel_size=1, activation="relu"),
            # heatmap
            tf.keras.layers.Conv2D(
                filters=self.num_joints, kernel_size=3, padding="same", activation=None)
        ])

        # === Regression ===

        #  In: 1, 64, 64, 48)
        self.conv12a = BlazeBlock(block_num=4, channel=96)    # input res: 64
        self.conv12b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=96, kernel_size=1, activation="relu")
        ])

        self.conv13a = BlazeBlock(block_num=5, channel=192)   # input res: 32
        self.conv13b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=192, kernel_size=1, activation="relu")
        ])

        self.conv14a = BlazeBlock(block_num=6, channel=288)   # input res: 16
        self.conv14b = tf.keras.models.Sequential([
            tf.keras.layers.DepthwiseConv2D(
                kernel_size=3, padding="same", activation=None),
            tf.keras.layers.Conv2D(
                filters=288, kernel_size=1, activation="relu")
        ])

        self.conv15 = tf.keras.models.Sequential([
            BlazeBlock(block_num=7, channel=288, channel_padding=0),
            BlazeBlock(block_num=7, channel=288, channel_padding=0)
        ])

        self.conv16 = tf.keras.models.Sequential([
            tf.keras.layers.GlobalAveragePooling2D(),
            # In: 1, 1, 1, 288
            tf.keras.layers.Dense(units=3*self.num_joints,
                                  activation=None),
            # tf.keras.layers.Reshape((self.num_joints, 3))
        ])

    def build_model(self):

        input_x = tf.keras.layers.Input(shape=(256, 256, 3))

        # In: 1x256x256x3
        # Out: 1x128x128x24
        x = self.conv1(input_x)

        # Block 2
        # In: 1x128x128x24
        # Out: 1x128x128x24
        x = x + self.conv2_1(x)
        x = tf.keras.activations.relu(x)

        # Block 3
        # In: 1x128x128x24
        # Out: 1x128x128x24
        x = x + self.conv2_2(x)
        y0 = tf.keras.activations.relu(x)

        # === Heatmap ===

        # In: 1, 128, 128, 24
        y1 = self.conv3(y0)
        y2 = self.conv4(y1)
        y3 = self.conv5(y2)
        y4 = self.conv6(y3)

        x = self.conv7a(y4) + self.conv7b(y3)
        x = self.conv8a(x) + self.conv8b(y2)
        # In: 1, 32, 32, 96
        x = self.conv9a(x) + self.conv9b(y1)
        # In: 1, 64, 64, 48
        y = self.conv10a(x) + self.conv10b(y0)
        # In: 1, 128, 128, 8
        heatmap = tf.keras.layers.Activation("sigmoid", name="heatmap")(self.conv11(y))

        # === Regression ===

        # Stop gradient for regression on 2-head model
        if self.model_type == ModelType.TWO_HEAD:
            x = tf.keras.backend.stop_gradient(x)
            y2 = tf.keras.backend.stop_gradient(y2)
            y3 = tf.keras.backend.stop_gradient(y3)
            y4 = tf.keras.backend.stop_gradient(y4)

        x = self.conv12a(x) + self.conv12b(y2)
        # In: 1, 32, 32, 96
        x = self.conv13a(x) + self.conv13b(y3)
        # In: 1, 16, 16, 192
        x = self.conv14a(x) + self.conv14b(y4)
        # In: 1, 8, 8, 288
        x = self.conv15(x)
        # In: 1, 2, 2, 288
        joints = self.conv16(x)
        joints = tf.keras.layers.Activation("sigmoid", name="joints")(joints)

        if self.model_type == ModelType.TWO_HEAD:
            return Model(inputs=input_x, outputs=[joints, heatmap])
        elif self.model_type == ModelType.HEATMAP:
            return Model(inputs=input_x, outputs=heatmap)
        elif self.model_type == ModelType.REGRESSION:
            return Model(inputs=input_x, outputs=joints)
        else:
            raise ValueError("Wrong model type.")