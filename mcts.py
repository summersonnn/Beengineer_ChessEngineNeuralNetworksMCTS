﻿#!/usr/bin/env python
import random
import math
import hashlib
import argparse
import time
import minichess as mic
import actionsdefined as ad
from copy import copy, deepcopy


"""
A quick Monte Carlo Tree Search implementation.  For more details on MCTS see See http://pubs.doc.ic.ac.uk/survey-mcts-methods/survey-mcts-methods.pdf
The State is just a game where you have NUM_TURNS and at turn i you can make
a choice from [-2,2,3,-3]*i and this to to an accumulated value.  The goal is for the accumulated value to be as close to 0 as possible.
The game is not very interesting but it allows one to study MCTS which is.  Some features 
of the example by design are that moves do not commute and early mistakes are more costly.  
In particular there are two models of best child that one can use 
"""

#MCTS scalar.  Larger scalar will increase exploitation, smaller will increase exploration. 
SCALAR=2
EXPAND_NUMBER = 5


class State():
	
	def __init__(self, BoardObject, color):
		self.availableActions = BoardObject.available_actions		# e.g Kg3, Ra4
		self.BoardObject = BoardObject				# Minichess object
		self.numberOfMoves = len(self.availableActions)
		self.moveCount = 0							#
		self.color = color							# "white" or "black"
		self.exclusive_board_string = ""  			# It will be calculated once the board representation is changed at the next_state function

	def build_exclusive_string(self):
		self.exclusive_board_string =""
		for i in range(6):
			for j in range(3):
				self.exclusive_board_string += self.BoardObject.board[i][j]
			
	def next_state(self):
		print("--------------next_state function-------------")
		next = deepcopy(self)
		next.color = "white" if self.color == "black" else "black"
		nextActionNumber = self.availableActions[random.randint(0, self.numberOfMoves - 1)] #e.g 145

		inv_actions = {v: k for k, v in ad.actions.items()}
		current_action = inv_actions[nextActionNumber]
		print("Current_action:" + current_action)
		del inv_actions
		
		#Get notation before move and current coorbit, empty the squre piece will be moved from, put zero to old coorbit position
		pieceNotationBeforeMove = next.BoardObject.board[int(current_action[0])][int(current_action[1])]	#e.g "+P"
		oldcoorBit = mic.coorToBitVector(int(current_action[0]), int(current_action[1]), pieceNotationBeforeMove) #e.g 30
		
		pieceNotationAfterMove = pieceNotationBeforeMove[0] + current_action[-1]
		color = "white" if pieceNotationAfterMove[0] == "+" else "black"
		promoted = True if len(current_action) == 6 else False
		ListToUse = next.BoardObject.WhitePieceList if pieceNotationAfterMove[0] == '+' else self.BoardObject.BlackPieceList
		otherList = next.BoardObject.WhitePieceList if pieceNotationAfterMove[0] == '-' else self.BoardObject.BlackPieceList
		
		#If capture happened, obtain the BitBoard repr. of captured piece, then remove the piece object from piece object list
		capturedPieceNotation = self.BoardObject.board[int(current_action[2])][int(current_action[3])]

		if capturedPieceNotation != "XX":
			capturedPieceBit = mic.coorToBitVector(int(current_action[2]), int(current_action[3]), capturedPieceNotation)
			next.BoardObject.bitVectorBoard[capturedPieceBit] = 0
			next.BoardObject.removeCapturedPiece(capturedPieceBit, otherList)
			

		#Update the board, obtain the new Bitboard repr. of the piece and update the bitvectorboard accordingly
		next.BoardObject.board[int(current_action[2])][int(current_action[3])] = pieceNotationAfterMove
		print(pieceNotationAfterMove)
		newcoorBit = mic.coorToBitVector(int(current_action[2]), int(current_action[3]), pieceNotationAfterMove)
		next.BoardObject.bitVectorBoard[newcoorBit] = 1

		next.BoardObject.board[int(current_action[0])][int(current_action[1])] = "XX"
		next.BoardObject.bitVectorBoard[oldcoorBit] = 0

		#Call the step function of the object, to make it renew itself (if the object is still valid, which means promotion did not happen)
		if not promoted:
			for i in ListToUse:
				if i.BitonBoard == oldcoorBit:
					i.step(newcoorBit, int(current_action[2]), int(current_action[3]) ) 
		#if promoted, create a new object and kill the pawn object
		else:
			ListToUse += Rook(color, int(current_action[2]), int(current_action[3]), self)	#Warning! Possible costly operation. Test it.
			#Not captured, but since promoted, pawn object must be deleted
			next.removeCapturedPiece(oldcoorBit, ListToUse)

		next.build_exclusive_string()	#New exclusive string is constructed, ready for being hashed
		next.moveCount += 1	#In the new node, movecount will be one more
		next.availableActions.clear()	#In the new node, we don't need the parent's available actions as they can be no longer valid actions
		next.availableActions = next.BoardObject.calculate_available_actions(next.color)	#Calc new available actions for the board object and pass it to State object member
		next.numberOfMoves = len(next.availableActions)
		return next
	def terminal(self):
		#Minichess için buradaki kontrol "action space 0'a düşmüşse (matsa)" olacak
		if self.moveCount > 30 or len(self.BoardObject.WhitePieceList) == 0 or len(self.BoardObject.BlackPieceList) == 0:
			return True
		return False
	def reward(self):
		if len(board.WhitePieceList) == 0:
			reward = 1 if self.color == "black" else -1
		elif len(board.BlackPieceList) == 0:
			reward = 1 if self.color == "white" else -1
		elif self.moveCount > 30:
			reward = 1 if (self.color == "white" and len(self.board.WhitePieceList) > len(self.board.BlackPieceList) or self.color == "black" and len(self.board.WhitePieceList) < len(self.board.BlackPieceList)) else -1
		else: #eşitler
			reward = 0
		
		return reward

	def __hash__(self):
		return int(hashlib.md5(self.exclusive_board_string.encode('utf-8')).hexdigest(),16)
	def __eq__(self,other):
		if hash(self)==hash(other):
			return True
		return False
	def __repr__(self):
		return self.board.print()	

class Node():
	def __init__(self, state, parent=None):
		self.visits=0
		self.reward=0.0	
		self.state=state
		self.children=[]
		self.parent=parent	
	def add_child(self, child_state):
		child = Node(child_state, self)
		self.children.append(child)
	def __repr__(self):
		s="Node; children: %d; visits: %d; Cum reward: %f Avg reward: %.2f"%(len(self.children),self.visits,self.reward, self.reward/self.visits)
		return s
		

#Verilen süre içinde simülasyon ve backup yaparak node rewardlarını günceller. Süre sonunda en iyi child döner.
def UCTSEARCH(root, timeout):
	timeout_start = time.time()

	while time.time() < timeout_start + timeout:
		afterTraverse=TRAVERSAL(root)
		if (afterTraverse.visits != 0):
			afterTraverse = EXPAND(afterTraverse, EXPAND_NUMBER)
	
		reward = ROLLOUT(afterTraverse.state)
		BACKUP(afterTraverse,reward)
	return BESTCHILD(root,0)

#Sürekli best child'ı seçerek leaf node'a ulaştırır. Buradan ilerde ya expand edilecek ya rollout yapılacak.
def TRAVERSAL(node):
	while len(node.children) != 0:
		node=BESTCHILD(node,SCALAR)
	return node
 
#Leaf node expand ettirir. Oluşturulacak child sayısı parametre olarak verilir.
def EXPAND(node, expandNumber):
	for i in range(expandNumber):
		tried_children=[c.state for c in node.children]
		new_state=node.state.next_state()
		while new_state in tried_children:
			new_state=node.state.next_state()
		node.add_child(new_state)
		tried_children += [new_state]
	return node.children[-1]

def BESTCHILD(node,scalar):
	bestscore=-10000
	bestchildren=[]

	for c in node.children:
		if c.visits == 0:
			score = 9999999
		else:
			exploit=c.reward/c.visits
			explore=math.sqrt(math.log(node.visits)/float(c.visits))	
			score=exploit+scalar*explore
		if score==bestscore:
			bestchildren.append(c)
		if score>bestscore:
			bestchildren=[c]
			bestscore=score
	if len(bestchildren)==0:
		print("OOPS: no best child found, probably fatal")
	return random.choice(bestchildren)

def ROLLOUT(state):
	while state.terminal()==False:
		state=state.next_state()
	return state.reward()

def BACKUP(node,reward):
	while node!=None:
		node.visits+=1
		node.reward+=reward
		node=node.parent
	return

def initializeTree(boardobject, color, timeout):
	root = Node(State(boardobject, color))
	root.state.build_exclusive_string()	#exclusive string for root is constructed (for hashing)
	root.visits = 1

	result = UCTSEARCH(root, timeout)
	print("At %d level, state: %s" %(i+1, result.state.word))
	print("At this level, all nodes looks like the following: ")
	for i,c in enumerate(root.children):
		print(i,c)
	root = result
	print("\n")
