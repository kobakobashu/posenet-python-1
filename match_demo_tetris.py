import tensorflow as tf
import cv2
import time
import argparse
import csv
import posenet
import numpy as np
# -*- coding:utf-8 -*-

# ここからテトリス

import tkinter as tk
import random

# 定数
BLOCK_SIZE = 25  # ブロックの縦横サイズpx
FIELD_WIDTH = 10  # フィールドの幅
FIELD_HEIGHT = 25  # フィールドの高さ

MOVE_LEFT = 0  # 左にブロックを移動することを示す定数
MOVE_RIGHT = 1  # 右にブロックを移動することを示す定数
MOVE_DOWN = 2  # 下にブロックを移動することを示す定数

# ブロックを構成する正方形のクラス
class TetrisSquare():
    def __init__(self, x=0, y=0, color="gray"):
        '１つの正方形を作成'
        self.x = x
        self.y = y
        self.color = color

    def set_cord(self, x, y):
        '正方形の座標を設定'
        self.x = x
        self.y = y

    def get_cord(self):
        '正方形の座標を取得'
        return int(self.x), int(self.y)

    def set_color(self, color):
        '正方形の色を設定'
        self.color = color

    def get_color(self):
        '正方形の色を取得'
        return self.color

    def get_moved_cord(self, direction):
        '移動後の正方形の座標を取得'

        # 移動前の正方形の座標を取得
        x, y = self.get_cord()

        # 移動方向を考慮して移動後の座標を計算
        if direction == MOVE_LEFT:
            return x - 1, y
        elif direction == MOVE_RIGHT:
            return x + 1, y
        elif direction == MOVE_DOWN:
            return x, y + 1
        else:
            return x, y

# テトリス画面を描画するキャンバスクラス
class TetrisCanvas(tk.Canvas):
    def __init__(self, master, field):
        'テトリスを描画するキャンバスを作成'

        canvas_width = field.get_width() * BLOCK_SIZE
        canvas_height = field.get_height() * BLOCK_SIZE

        # tk.Canvasクラスのinit
        super().__init__(master, width=canvas_width, height=canvas_height, bg="white")

        # キャンバスを画面上に設置
        self.place(x=25, y=25)

        # 10x20個の正方形を描画することでテトリス画面を作成
        for y in range(field.get_height()):
            for x in range(field.get_width()):
                square = field.get_square(x, y)
                x1 = x * BLOCK_SIZE
                x2 = (x + 1) * BLOCK_SIZE
                y1 = y * BLOCK_SIZE
                y2 = (y + 1) * BLOCK_SIZE
                self.create_rectangle(
                    x1, y1, x2, y2,
                    outline="white", width=1,
                    fill=square.get_color()
                )

        # 一つ前に描画したフィールドを設定
        self.before_field = field

    def update(self, field, block):
        'テトリス画面をアップデート'

        # 描画用のフィールド（フィールド＋ブロック）を作成
        new_field = TetrisField()
        for y in range(field.get_height()):
            for x in range(field.get_width()):
                square = field.get_square(x, y)
                color = square.get_color()

                new_square = new_field.get_square(x, y)
                new_square.set_color(color)

        # フィールドにブロックの正方形情報を合成
        if block is not None:
            block_squares = block.get_squares()
            for block_square in block_squares:
                # ブロックの正方形の座標と色を取得
                x, y = block_square.get_cord()
                color = block_square.get_color()

                # 取得した座標のフィールド上の正方形の色を更新
                new_field_square = new_field.get_square(x, y)
                new_field_square.set_color(color)

        # 描画用のフィールドを用いてキャンバスに描画
        for y in range(field.get_height()):
            for x in range(field.get_width()):

                # (x,y)座標のフィールドの色を取得
                new_square = new_field.get_square(x, y)
                new_color = new_square.get_color()

                # (x,y)座標が前回描画時から変化ない場合は描画しない
                before_square = self.before_field.get_square(x, y)
                before_color = before_square.get_color()
                if(new_color == before_color):
                    continue

                x1 = x * BLOCK_SIZE
                x2 = (x + 1) * BLOCK_SIZE
                y1 = y * BLOCK_SIZE
                y2 = (y + 1) * BLOCK_SIZE
                # フィールドの各位置の色で長方形描画
                self.create_rectangle(
                    x1, y1, x2, y2,
                    outline="white", width=1, fill=new_color
                )

        # 前回描画したフィールドの情報を更新
        self.before_field = new_field

# 積まれたブロックの情報を管理するフィールドクラス
class TetrisField():
    def __init__(self):
        self.width = FIELD_WIDTH
        self.height = FIELD_HEIGHT

        # フィールドを初期化
        self.squares = []
        for y in range(self.height):
            for x in range(self.width):
                # フィールドを正方形インスタンスのリストとして管理
                self.squares.append(TetrisSquare(x, y, "gray"))

    def get_width(self):
        'フィールドの正方形の数（横方向）を取得'

        return self.width

    def get_height(self):
        'フィールドの正方形の数（縦方向）を取得'

        return self.height

    def get_squares(self):
        'フィールドを構成する正方形のリストを取得'

        return self.squares

    def get_square(self, x, y):
        '指定した座標の正方形を取得'

        return self.squares[y * self.width + x]

    def judge_game_over(self, block):
        'ゲームオーバーかどうかを判断'

        # フィールド上で既に埋まっている座標の集合作成
        no_empty_cord = set(square.get_cord() for square
                            in self.get_squares() if square.get_color() != "gray")

        # ブロックがある座標の集合作成
        block_cord = set(square.get_cord() for square
                         in block.get_squares())

        # ブロックの座標の集合と
        # フィールドの既に埋まっている座標の集合の積集合を作成
        collision_set = no_empty_cord & block_cord

        # 積集合が空であればゲームオーバーではない
        if len(collision_set) == 0:
            ret = False
        else:
            ret = True

        return ret

    def judge_can_move(self, block, direction):
        '指定した方向にブロックを移動できるかを判断'

        # フィールド上で既に埋まっている座標の集合作成
        no_empty_cord = set(square.get_cord() for square
                            in self.get_squares() if square.get_color() != "gray")

        # 移動後のブロックがある座標の集合作成
        move_block_cord = set(square.get_moved_cord(direction) for square
                              in block.get_squares())

        # フィールドからはみ出すかどうかを判断
        for x, y in move_block_cord:

            # はみ出す場合は移動できない
            if x < 0 or x >= self.width or \
                    y < 0 or y >= self.height:
                return False

        # 移動後のブロックの座標の集合と
        # フィールドの既に埋まっている座標の集合の積集合を作成
        collision_set = no_empty_cord & move_block_cord

        # 積集合が空なら移動可能
        if len(collision_set) == 0:
            ret = True
        else:
            ret = False

        return ret

    def fix_block(self, block):
        'ブロックを固定してフィールドに追加'

        for square in block.get_squares():
            # ブロックに含まれる正方形の座標と色を取得
            x, y = square.get_cord()
            color = square.get_color()

            # その座標と色をフィールドに反映
            field_square = self.get_square(x, y)
            field_square.set_color(color)

    def delete_line(self):
        '行の削除を行う'

        # 全行に対して削除可能かどうかを調べていく
        for y in range(self.height):
            for x in range(self.width):
                # 行内に１つでも空があると消せない
                square = self.get_square(x, y)
                if(square.get_color() == "gray"):
                    # 次の行へ
                    break
            else:
                # break されなかった場合はその行は空きがない
                # この行を削除し、この行の上側にある行を１行下に移動
                for down_y in range(y, 0, -1):
                    for x in range(self.width):
                        src_square = self.get_square(x, down_y - 1)
                        dst_square = self.get_square(x, down_y)
                        dst_square.set_color(src_square.get_color())
                # 一番上の行は必ず全て空きになる
                for x in range(self.width):
                    square = self.get_square(x, 0)
                    square.set_color("gray")

# テトリスのブロックのクラス
class TetrisBlock():
    def __init__(self):
        'テトリスのブロックを作成'

        # ブロックを構成する正方形のリスト
        self.squares = []

        # ブロックの形をランダムに決定
        block_type = random.randint(1, 6)

        # ブロックの形に応じて４つの正方形の座標と色を決定
        if block_type == 1:
            color = "red"
            cords = [
                [FIELD_WIDTH / 2, 0],
                [FIELD_WIDTH / 2, 1],
                [FIELD_WIDTH / 2, 2],
                [FIELD_WIDTH / 2, 3],
            ]
        elif block_type == 2:
            color = "blue"
            cords = [
                [FIELD_WIDTH / 2, 0],
                [FIELD_WIDTH / 2, 1],
                [FIELD_WIDTH / 2 - 1, 0],
                [FIELD_WIDTH / 2 - 1, 1],
            ]
        elif block_type == 3:
            color = "green"
            cords = [
                [FIELD_WIDTH / 2 - 1, 0],
                [FIELD_WIDTH / 2, 0],
                [FIELD_WIDTH / 2, 1],
                [FIELD_WIDTH / 2, 2],
            ]
        elif block_type == 4:
            color = "orange"
            cords = [
                [FIELD_WIDTH / 2, 0],
                [FIELD_WIDTH / 2 - 1, 0],
                [FIELD_WIDTH / 2 - 1, 1],
                [FIELD_WIDTH / 2 - 1, 2],
            ]
        elif block_type == 5:
            color = "yellow"
            cords = [
                [FIELD_WIDTH / 2, 0],
                [FIELD_WIDTH / 2, 1],
                [FIELD_WIDTH / 2 - 1, 1],
                [FIELD_WIDTH / 2 - 1, 2],
            ]
        elif block_type == 6:
            color = "brown"
            cords = [
                [FIELD_WIDTH / 2 - 1, 0],
                [FIELD_WIDTH / 2 - 1, 1],
                [FIELD_WIDTH / 2, 1],
                [FIELD_WIDTH / 2, 2],
            ]
            

        # 決定した色と座標の正方形を作成してリストに追加
        for cord in cords:
            self.squares.append(TetrisSquare(cord[0], cord[1], color))

    def get_squares(self):
        'ブロックを構成する正方形を取得'

        # return [square for square in self.squares]
        return self.squares

    def move(self, direction):
        'ブロックを移動'

        # ブロックを構成する正方形を移動
        for square in self.squares:
            x, y = square.get_moved_cord(direction)
            square.set_cord(x, y)

# テトリスゲームを制御するクラス
class TetrisGame():

    def __init__(self, master):
        'テトリスのインスタンス作成'

        # ブロック管理リストを初期化
        self.field = TetrisField()

        # 落下ブロックをセット
        self.block = None

        # テトリス画面をセット
        self.canvas = TetrisCanvas(master, self.field)

        # テトリス画面アップデート
        self.canvas.update(self.field, self.block)

    def start(self, func):
        'テトリスを開始'

        # 終了時に呼び出す関数をセット
        self.end_func = func

        # ブロック管理リストを初期化
        self.field = TetrisField()

        # 落下ブロックを新規追加
        self.new_block()

    def new_block(self):
        'ブロックを新規追加'

        # 落下中のブロックインスタンスを作成
        self.block = TetrisBlock()

        if self.field.judge_game_over(self.block):
            self.end_func()
            print("GAMEOVER")

        # テトリス画面をアップデート
        self.canvas.update(self.field, self.block)

    def move_block(self, direction):
        'ブロックを移動'

        # 移動できる場合だけ移動する
        if self.field.judge_can_move(self.block, direction):

            # ブロックを移動
            self.block.move(direction)

            # 画面をアップデート
            self.canvas.update(self.field, self.block)

        else:
            # ブロックが下方向に移動できなかった場合
            if direction == MOVE_DOWN:
                # ブロックを固定する
                self.field.fix_block(self.block)
                self.field.delete_line()
                self.new_block()

# イベントを受け付けてそのイベントに応じてテトリスを制御するクラス
class EventHandller():
    def __init__(self, master, game):
        self.master = master

        # 制御するゲーム
        self.game = game

        # イベントを定期的に発行するタイマー
        self.timer = None

        # ゲームスタートボタンを設置
        button = tk.Button(master, text='START', command=self.start_event)
        button.place(x=25 + BLOCK_SIZE * FIELD_WIDTH + 25, y=30)

    def start_event(self):
        'ゲームスタートボタンを押された時の処理'

        # テトリス開始
        self.game.start(self.end_event)
        self.running = True

        # タイマーセット
        self.timer_start()

        # キー操作入力受付開始
        self.master.bind("<Left>", self.left_key_event)
        self.master.bind("<Right>", self.right_key_event)
        self.master.bind("<Down>", self.down_key_event)

    def end_event(self):
        'ゲーム終了時の処理'
        self.running = False

        # イベント受付を停止
        self.timer_end()
        self.master.unbind("<Left>")
        self.master.unbind("<Right>")
        self.master.unbind("<Down>")

    def timer_end(self):
        'タイマーを終了'

        if self.timer is not None:
            self.master.after_cancel(self.timer)
            self.timer = None

    def timer_start(self):
        'タイマーを開始'

        if self.timer is not None:
            # タイマーを一旦キャンセル
            self.master.after_cancel(self.timer)

        # テトリス実行中の場合のみタイマー開始
        if self.running:
            # タイマーを開始
            self.timer = self.master.after(1000, self.timer_event)

    def left_key_event(self, event):
        '左キー入力受付時の処理'

        # ブロックを左に動かす
        self.game.move_block(MOVE_LEFT)

    def right_key_event(self, event):
        '右キー入力受付時の処理'

        # ブロックを右に動かす
        self.game.move_block(MOVE_RIGHT)

    def down_key_event(self, event):
        '下キー入力受付時の処理'

        # ブロックを下に動かす
        self.game.move_block(MOVE_DOWN)

        # 落下タイマーを再スタート
        self.timer_start()

    def timer_event(self):
        'タイマー満期になった時の処理'

        # 下キー入力受付時と同じ処理を実行
        self.down_key_event(None)


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        # アプリウィンドウの設定
        self.geometry("400x600")
        self.title("テトリス")

        # テトリス生成
        game = TetrisGame(self)

        # イベントハンドラー生成
        EventHandller(self, game)

# ここまでテトリス

parser = argparse.ArgumentParser()
parser.add_argument('--model', type=int, default=101)
parser.add_argument('--cam_id', type=int, default=0)
parser.add_argument('--cam_width', type=int, default=1280)
parser.add_argument('--cam_height', type=int, default=720)
parser.add_argument('--scale_factor', type=float, default=0.7125)
parser.add_argument('--match_model', type=str, default='./output_csv/motion_model.csv')
parser.add_argument('--file', type=str, default=None, help="Optionally use a video file instead of a live camera")
args = parser.parse_args()

def cos_sim(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def weightedDistanceMatching(poseVector1_x, poseVector1_y, vector1Confidences, vector1ConfidenceSum, poseVector2):
#   First summation
    summation1 = 1.0 / vector1ConfidenceSum
#   Second summation
    summation2 = 0
    for indent_num in range(len(poseVector1_x)):
        tempSum = vector1Confidences[indent_num] * ( abs(poseVector1_x[indent_num] -  poseVector2[indent_num]) + abs(poseVector1_y[indent_num] -  poseVector2[indent_num + len(poseVector1_x)]))
        summation2 = summation2 + tempSum
    return summation1 * summation2

def main():
# テトリスここから(mai)
    'main関数'

    # GUIアプリ生成
    app = Application()
    app.mainloop()
# テトリスここまで(main)    

def main2():
    with tf.Session() as sess:
        with open(args.match_model) as f:
            reader = csv.reader(f)
            motion_model = [row for row in reader]
        for i in range(len(motion_model)):
            motion_model[i][1:] = list(map(lambda x:float(x), motion_model[i][1:]))

        model_cfg, model_outputs = posenet.load_model(args.model, sess)
        output_stride = model_cfg['output_stride']
        if args.file is not None:
            cap = cv2.VideoCapture(args.file)
        else:
            cap = cv2.VideoCapture(args.cam_id)
        cap.set(3, args.cam_width)
        cap.set(4, args.cam_height)

        start = time.time()
        frame_count = 0
        while True:
            input_image, display_image, output_scale = posenet.read_cap(
                cap, scale_factor=args.scale_factor, output_stride=output_stride)

            heatmaps_result, offsets_result, displacement_fwd_result, displacement_bwd_result = sess.run(
                model_outputs,
                feed_dict={'image:0': input_image}
            )

            pose_scores, keypoint_scores, keypoint_coords = posenet.decode_multi.decode_multiple_poses(
                heatmaps_result.squeeze(axis=0),
                offsets_result.squeeze(axis=0),
                displacement_fwd_result.squeeze(axis=0),
                displacement_bwd_result.squeeze(axis=0),
                output_stride=output_stride,
                max_pose_detections=10,
                min_pose_score=0.15)

            keypoint_coords *= output_scale

            if pose_scores[0] > 0.5:
                # clip
                pose_coords_x = keypoint_coords[0,:,0] - min(keypoint_coords[0,:,0])
                pose_coords_y = keypoint_coords[0,:,1] - min(keypoint_coords[0,:,1])

                # normalize
                x_l2_norm = np.linalg.norm(keypoint_coords[0,:,0],ord=2)
                pose_coords_x = (pose_coords_x / x_l2_norm).tolist()
                y_l2_norm = np.linalg.norm(keypoint_coords[0,:,1],ord=2)
                pose_coords_y = (pose_coords_y / y_l2_norm).tolist()

                distance_min = 1000000
                min_num = -1
                for teach_num in range(len(motion_model)):
                    distance = weightedDistanceMatching(pose_coords_x, pose_coords_y, keypoint_scores[0,:], pose_scores[0], motion_model[teach_num][1:35])
                    # distance = cos_sim(pose_coords_x + pose_coords_y, motion_model[teach_num][1:35])
                    if distance < distance_min:
                        distance_min = distance
                        min_num = teach_num
                    print(distance)
                cv2.putText(display_image, motion_model[min_num][0] + "aiueo", (int(keypoint_coords[0,:,0][0]),int(keypoint_coords[0,:,0][1])), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), thickness=2)
                print(motion_model[min_num][0])

            overlay_image = posenet.draw_skel_and_kp(
                display_image, pose_scores, keypoint_scores, keypoint_coords,
                min_pose_score=0.15, min_part_score=0.1)

            cv2.imshow('posenet', overlay_image)
            # TODO this isn't particularly fast, use GL for drawing and display someday...
            
            frame_count += 1
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        print('Average FPS: ', frame_count / (time.time() - start))


if __name__ == "__main__":
    main()
    main2()