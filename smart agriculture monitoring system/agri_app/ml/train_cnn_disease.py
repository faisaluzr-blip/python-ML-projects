"""
TensorFlow CNN training template for real leaf disease datasets.

Dataset layout:
data/leaf_dataset/
  Healthy Leaf/
  Leaf Rust/
  Early Blight/
  Bacterial Spot/
  Powdery Mildew/

Install TensorFlow separately when needed:
pip install tensorflow
python -m agri_app.ml.train_cnn_disease
"""

from pathlib import Path


def main():
    import tensorflow as tf

    dataset_dir = Path("data/leaf_dataset")
    if not dataset_dir.exists():
        raise SystemExit("Create data/leaf_dataset with one folder per disease class before training.")

    train = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="training",
        seed=42,
        image_size=(160, 160),
        batch_size=32,
    )
    val = tf.keras.utils.image_dataset_from_directory(
        dataset_dir,
        validation_split=0.2,
        subset="validation",
        seed=42,
        image_size=(160, 160),
        batch_size=32,
    )
    class_names = train.class_names

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Rescaling(1.0 / 255),
            tf.keras.layers.Conv2D(32, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(64, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(128, 3, activation="relu"),
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dropout(0.25),
            tf.keras.layers.Dense(len(class_names), activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train, validation_data=val, epochs=12)
    Path("models").mkdir(exist_ok=True)
    model.save("models/leaf_disease_cnn.keras")
    Path("models/leaf_classes.txt").write_text("\n".join(class_names), encoding="utf-8")
    print("Saved models/leaf_disease_cnn.keras")


if __name__ == "__main__":
    main()
