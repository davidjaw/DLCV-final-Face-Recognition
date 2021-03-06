import tensorflow as tf
import model
from data_reader import TestDataReader, DataReader
import argparse
import os
import time


def get_args():
    parser = argparse.ArgumentParser(description='Face recognition')
    parser.add_argument('--data_path', type=str, default='./dlcv_final_2_dataset/test/', help='path to the testset folder')
    parser.add_argument('--weight_path', type=str, default='./weight/', help='path to store/read weights')
    parser.add_argument('--model_name', type=str, default='teacher.ckpt',
                        help='filename of trained model\'s weightfile')
    parser.add_argument('--batch_size', type=int, default=100, help='Number of instance in each testing batch')
    parser.add_argument('--out_path', type=str, default='./out/', help='path to store the output file')
    parser.add_argument('--is_teacher', action='store_true', help='Either use the teacher network or student network')
    parser.add_argument('--light', action='store_true', help='Either to use light model or not')
    return parser.parse_args()


def main(args):
    print(args)
    with tf.variable_scope('Data_Generator'):
        test_data_reader = TestDataReader(data_path=args.data_path)
        data_reader = DataReader(data_path=None)
        test_x, test_num = test_data_reader.get_instance(batch_size=args.batch_size)

    if args.is_teacher:
        network = model.TeacherNetwork()
        logits, _ = network.build_network(test_x, class_num=len(data_reader.dict_class.keys()), reuse=False,
                                          is_train=False, dropout=1)
    else:
        network = model.StudentNetwork(len(data_reader.dict_class.keys()))
        logits, _ = network.build_network(test_x, False, False, light=args.light)
    pred = tf.nn.softmax(logits, -1)
    pred = tf.argmax(pred, -1, output_type=tf.int32)

    train_params = tf.contrib.slim.get_variables()
    saver = tf.train.Saver(var_list=train_params)

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    saver.restore(sess, args.weight_path + args.model_name)

    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(coord=coord, sess=sess)
    tf.Graph().finalize()

    if not os.path.exists(args.out_path):
        os.mkdir(args.out_path)
    out_f = open(args.out_path + 'out_{}.txt'.format(args.model_name), 'w')
    out_f.write('id,ans\n')
    instance_cnt = 0
    step = 0
    total_time = 0
    while step * args.batch_size < test_num:
        step += 1
        start_time = time.time()
        np_pred = sess.run(pred)
        total_time += time.time() - start_time
        for i in range(np_pred.shape[0]):
            out_f.write('{},{}\n'.format(instance_cnt + 1, data_reader.dict_class[np_pred[i]]))
            instance_cnt += 1
            if instance_cnt >= test_num:
                break

    out_f.close()
    coord.request_stop()
    coord.join(threads)
    print('Total time: {:.2f} secs with {:d} instance. fps={:.2f}'.format(
        total_time, step * args.batch_size, step * args.batch_size / total_time))


if __name__ == '__main__':
    main(get_args())
