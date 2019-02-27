import math
import os
import tensorflow as tf

from conv2conv import Conv2Conv
from data_helper import DataSet


flags = tf.flags
FLAGS = flags.FLAGS

flags.DEFINE_integer("hidden_size", 1024, "Number of hidden units in each layer")
flags.DEFINE_integer("num_layers", 7, "Number of layers in each encoder and decoder")
flags.DEFINE_integer("embedding_size", 500, "Embedding dimensions of encoder and decoder inputs")
flags.DEFINE_integer("kernel_size", 3, "kernel size of conv")
flags.DEFINE_integer("num_filters", 2048, "filter numbers of conv")
flags.DEFINE_float("learning_rate", 1e-3, "Learning rate")
flags.DEFINE_integer("batch_size", 16, "Batch size")
flags.DEFINE_float("keep_prob", 0.9, "keep dropout prob")
flags.DEFINE_integer("epochs", 30, "Maximum # of training epochs")

flags.DEFINE_float("ratio", 0.01, "eval data ratio")

flags.DEFINE_integer("steps_per_checkpoint", 100, "Save model checkpoint every this iteration")
flags.DEFINE_string("model_dir", "model/", "Path to save model checkpoints")
flags.DEFINE_string("model_name", "gec", "File name used for model checkpoints")

flags.DEFINE_string("source_file", "data/lang-8/lang8-train.en", "source sentence file path")
flags.DEFINE_string("target_file", "data/lang-8/lang8-train.gec", "target sentence file path")


dataSet = DataSet(FLAGS.embedding_size, FLAGS.source_file, FLAGS.target_file, FLAGS.batch_size,
                  FLAGS.ratio)

# 生成训练数据和测试数据
dataSet.gen_train_eval()
vocab_size = len(dataSet.idx_to_word)

gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9, allow_growth=True)
config = tf.ConfigProto(log_device_placement=False, allow_soft_placement=True, gpu_options=gpu_options)

with tf.device("/device:GPU:0"):
    with tf.Session(config=config) as sess:
        model = Conv2Conv(FLAGS.embedding_size, FLAGS.hidden_size, vocab_size, FLAGS.num_layers,
                          FLAGS.kernel_size, FLAGS.num_filters, is_training=True)

        saver = tf.train.Saver(tf.global_variables())

        sess.run(tf.global_variables_initializer())

        current_step = 0
        summary_writer = tf.summary.FileWriter(FLAGS.model_dir, graph=sess.graph)

        for epoch in range(FLAGS.epochs):
            print("----- Epoch {}/{} -----".format(epoch + 1, FLAGS.epochs))

            for batch in dataSet.next_batch(dataSet.train_data):
                loss, summary = model.train(sess, batch, FLAGS.keep_prob)
                perplexity = math.exp(float(loss)) if loss < 300 else float("inf")
                current_step += 1
                print("train: step: {}, loss: {}, perplexity: {}".format(current_step, loss, perplexity))
                if current_step % FLAGS.steps_per_checkpoint == 0:

                    eval_losses = []
                    eval_perplexities = []
                    for eval_batch in dataSet.next_batch(dataSet.eval_data):
                        eval_loss, eval_summary = model.eval(sess, eval_batch, 1.0)
                        eval_perplexity = math.exp(float(loss)) if loss < 300 else float("inf")

                        eval_losses.append(eval_loss)
                        eval_perplexities.append(eval_perplexity)
                    print("eval: step: {}, loss: {}, perplexity: {}".format(current_step,
                                                                            sum(eval_losses) / len(eval_losses),
                                                                            sum(eval_perplexities) / len(eval_perplexities)))
                    checkpoint_path = os.path.join(FLAGS.model_dir, FLAGS.model_name)
                    saver.save(sess, checkpoint_path, global_step=current_step)