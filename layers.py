"""Classes for SimGNN modules."""

import torch

#除了pyg原生的GCN，论文使用自创 图注意力机制的层  和 NTN层  都在layers.py手动实现
class AttentionModule(torch.nn.Module):
    """
    SimGNN Attention Module to make a pass on graph.
    """
    def __init__(self, args):
        """
        :param args: Arguments object.
        """
        super(AttentionModule, self).__init__()
        self.args = args
        self.setup_weights()
        self.init_parameters()

    def setup_weights(self):
        """
        Defining weights.
        """
        #？？？？？？？？？？？？？？？
        self.weight_matrix = torch.nn.Parameter(torch.Tensor(self.args.filters_3,
                                                             self.args.filters_3))

    def init_parameters(self):
        """
        Initializing weights.
        """
        #？？？？？？？？？？？？？？？？？？
        torch.nn.init.xavier_uniform_(self.weight_matrix)

    #每个层都有一个forward方法，在SimGNN的forward中进行数据的显式输入？？？？？？？？？？？？
    #注意力机制！！！！！！！！！！！
    def forward(self, embedding):   #embedding即左右节点的输入
        """
        Making a forward propagation pass to create a graph level representation.
        :param embedding: Result of the GCN.
        :return representation: A graph level representation vector.
        """
        #全局上下文信息：卷积层的输出*注意力权重矩阵，生成维度N*f3的矩阵，即N个节点的嵌入
        #dim=0，将N个节点的嵌入求平均为1个，来作为全局表征
        #global_context 即c
        global_context = torch.mean(torch.matmul(embedding, self.weight_matrix), dim=0)     #matmul也是矩阵相乘
        transformed_global = torch.tanh(global_context)
        #将每个节点的嵌入与全局上下文信息作内积，来刻画相似性 sigmoid()是f2函数
        sigmoid_scores = torch.sigmoid(torch.mm(embedding, transformed_global.view(-1, 1))) #.view进行reshape
        #得到最终的Graph Embedding: Global Context-Aware Attention
        representation = torch.mm(torch.t(embedding), sigmoid_scores)
        return representation

class TenorNetworkModule(torch.nn.Module):
    """
    SimGNN Tensor Network module to calculate similarity vector.
    """
    def __init__(self, args):
        """
        :param args: Arguments object.
        """
        super(TenorNetworkModule, self).__init__()
        self.args = args
        self.setup_weights()
        self.init_parameters()

    def setup_weights(self):#？？？？？？？？？？何含义
        """
        Defining weights.
        """
        self.weight_matrix = torch.nn.Parameter(torch.Tensor(self.args.filters_3,       #图中绿色部分
                                                             self.args.filters_3,       #图中黄色部分
                                                             self.args.tensor_neurons)) #   三维张量，即K 蓝色部分

        self.weight_matrix_block = torch.nn.Parameter(torch.Tensor(self.args.tensor_neurons,
                                                                   2*self.args.filters_3))  #第二部分，因为两个连接起来所以是2*
        self.bias = torch.nn.Parameter(torch.Tensor(self.args.tensor_neurons, 1))

    def init_parameters(self):
        """
        Initializing weights.
        """
        torch.nn.init.xavier_uniform_(self.weight_matrix)
        torch.nn.init.xavier_uniform_(self.weight_matrix_block)
        torch.nn.init.xavier_uniform_(self.bias)

    #？？？？？？？？？？？？？？？？
    def forward(self, embedding_1, embedding_2):
        """
        Making a forward propagation pass to create a similarity vector.
        :param embedding_1: Result of the 1st embedding after attention.
        :param embedding_2: Result of the 2nd embedding after attention.
        :return scores: A similarity score vector.
        """
        #逐个相乘再相连，最终得到K（论文中的超参数）*1的向量
        scoring = torch.mm(torch.t(embedding_1), self.weight_matrix.view(self.args.filters_3, -1))
        scoring = scoring.view(self.args.filters_3, self.args.tensor_neurons)
        scoring = torch.mm(torch.t(scoring), embedding_2)
        #结果也是K+1，然后加上偏量经过一层ReLU，就得到最终输出。？？？？？？？？？？
        combined_representation = torch.cat((embedding_1, embedding_2))
        block_scoring = torch.mm(self.weight_matrix_block, combined_representation)
        scores = torch.nn.functional.relu(scoring + block_scoring + self.bias)
        return scores
