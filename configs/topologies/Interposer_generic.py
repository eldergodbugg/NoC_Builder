from common import FileSystemConfig
from topologies.BaseTopology import SimpleTopology

from m5.objects import *
from m5.params import *
import math
import random
from itertools import product

class Interposer_Mesh(SimpleTopology):
    description = "Interposer_Mesh"

    def __init__(self, controllers):
        self.node = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        #options --> can add in Network.py (more inputs from command line)
        nodes = self.nodes
        
        #TODO: Change "meshes" to "chiplets" later.
        # Chiplets can be of any topology.

        #Note: Type of topology for interposer and chiplets
        # currently supports only "mesh"
        mesh_sizes              = options.mesh_sizes    #[X,Y,L] --> X,Y == Dimensions, L == Level info
        mesh_size_count         = options.mesh_size_count
        num_cpus                = options.num_cpus
        interposer_sizes        = options.interposer_sizes
        interposer_size_count   = options.interposer_size_count
        link_latency            = options.link_latency  # used by simple and garnet
        router_latency          = options.router_latency  # only used by garnet

        assert(len(mesh_size_count) == len(mesh_sizes))
        assert(len(interposer_sizes) == len(interposer_size_count))

        # -------------------------------
        # ---------- Chiplets -----------
        # -------------------------------
        mesh_routers_count = 0
        mesh_routers = {}
        num_meshes = 0

        for i in range(len(mesh_size_count)):
            size = mesh_sizes[i]
            count = mesh_size_count[i]

            # Adding to list of routers
            for j in range(count):
                router_id_offset = mesh_routers_count
                for m in range(size[0]):
                    row_offset = m*size[1]
                    for n in range(size[1]):
                        level           = size[2]
                        chiplet_id      = num_meshes+j
                        router_id       = row_offset + n
                        router_coord    = (m,n)
                        mesh_routers[chiplet_id].append([Router(router_id = router_id_offset + row_offset + n, 
                                                        chiplet_id = chiplet_id, 
                                                        latency = router_latency
                                                        ), level, size, router_id, router_coord])
                mesh_routers_count += size[0] * size[1]
            num_meshes += count

        assert(mesh_routers_count == num_cpus)
        assert(num_meshes == sum(mesh_size_count))


        # ----------------------------------
        # ------------ Interposers ---------
        # ----------------------------------
        #TODO: RouteInfo (Chiplet number?)
        # Added in BasicRouter Class => chiplet_id

        interposer_routers_count = 0
        num_interposer_meshes = 0
        interposer_routers = {}

        for i in range(len(interposer_size_count)):
            size = interposer_sizes[i]
            count = interposer_size_count[i]

            for j in range(count):
                router_id_offset = mesh_routers_count + interposer_routers_count
                for m in range(size[0]):
                    row_offset = m*size[1]
                    for n in range(size[1]):
                        level = size[2]
                        chiplet_id      = num_meshes + num_interposer_meshes + j
                        router_id       = row_offset + n
                        router_coord    = (m, n)
                        interposer_routers[chiplet_id].append([Router(router_id = router_id_offset + row_offset + n, 
                                                              chiplet_id = chiplet_id, 
                                                              latency = router_latency
                                                              ), level, size, router_id, router_coord])
                interposer_routers_count += size[0] * size[1]
            num_interposer_meshes += count

        assert(interposer_routers_count >= 4*num_meshes)    # Assuming 4 links to each mesh chiplet from interposer
        assert(interposer_routers_count >= nodes)           # Assuming #I/O nodes lesser than I-size

        # How to connect? (Connectivity information needed)
        # Get it from the user --> run command (list containing connections to each transposer)

        # ---------------------------------
        # ---------- Connectivity ---------
        # ---------------------------------
        # 1. Levels: The "height" level at which each topology lies.
        #   - Helps in determining up-down connections to be made respectively
        #   - Only for boundary routing
        # 2. Mapping: I-I and M-I connections (I=interposer id; M=mesh id)
        #   - mapII :     I-I connections. List of [[i,i]...] pairs
        #   - mapMM :     M-M connections (through traffic connections info revealed here). List of [[m,m]...] pairs
        #   - mapIM :     I-M conections. List of [[i, m]...] pairs
        # 3. Order in which mesh/interposer info given matters? (Yes, for chiplet-id)

        # Mapping between different chiplet-ids (note: even interposers have their own chiplet-id)
        # TODO: Check if this can be done via a .json file
        mapII       = options.mapII
        mapMM       = options.mapMM
        mapIM       = options.mapIM

        # List of [up, down, II_cnt, IM_cnt]  --> which tracks the up-down links for each chiplet
        # To get chiplet-chiplet mapping

        Iconnections = [[[0,0],[0,0], 0, 0] for _ in range(num_interposer_meshes)] # --> [II_CNT[UP,DOWN], IM_CNT[..], TOTAL]
        Mconnections = [[[0,0],[0,0], 0, 0] for _ in range(num_meshes)]            # --> [MM_CNT[..], IM_CNT[..], TOTAL]
        UP          = 0
        DOWN        = 1
        II_CNT      = 0
        MM_CNT      = 0
        IM_CNT      = 1
        UP_TOTAL    = 2
        DOWN_TOTAL  = 3

        for II in mapII:
            # REQUIREMENT: User gives ids for meshes & interposers separately
            Ichiplet_id1 = II[0] + num_meshes
            Ichiplet_id2 = II[1] + num_meshes
            level1 = interposer_routers[Ichiplet_id1][1]
            level2 = interposer_routers[Ichiplet_id2][1]

            if level1 > level2:
                assert(level1 == level2+1)
                Iconnections[II[0]][II_CNT][DOWN]   += 1
                Iconnections[II[1]][II_CNT][UP]     += 1
                Iconnections[II[0]][DOWN_TOTAL]     += 1
                Iconnections[II[1]][UP_TOTAL]       += 1
            else:
                assert(level2 == level1+1)
                Iconnections[II[0]][II_CNT][UP]     += 1
                Iconnections[II[1]][II_CNT][DOWN]   += 1
                Iconnections[II[0]][UP_TOTAL]       += 1
                Iconnections[II[1]][DOWN_TOTAL]     += 1
        
        for MM in mapMM:
            Mchiplet_id1 = MM[0]
            Mchiplet_id2 = MM[1]
            level1 = mesh_routers[Mchiplet_id1][1]
            level2 = mesh_routers[Mchiplet_id2][1]

            if level1 > level2:
                assert(level1 == level2+1)
                Mconnections[Mchiplet_id1][MM_CNT][DOWN]    += 1
                Mconnections[Mchiplet_id2][MM_CNT][UP]      += 1
                Mconnections[Mchiplet_id1][DOWN_TOTAL]      += 1
                Mconnections[Mchiplet_id2][UP_TOTAL]        += 1
            else:
                assert(level2 == level1+1)
                Mconnections[Mchiplet_id1][MM_CNT][UP]      += 1
                Mconnections[Mchiplet_id2][MM_CNT][DOWN]    += 1
                Mconnections[Mchiplet_id1][UP_TOTAL]        += 1
                Mconnections[Mchiplet_id2][DOWN_TOTAL]      += 1
            
        for IM in mapIM:
            Ichiplet_id = IM[0] + num_meshes
            Mchiplet_id = IM[1]
            level1 = interposer_routers[Ichiplet_id][1]
            level2 = mesh_routers[Mchiplet_id][1]

            if level1 > level2:
                assert(level1 == level2+1)
                Iconnections[IM[0]][IM_CNT][DOWN]       += 1
                Mconnections[Mchiplet_id][IM_CNT][UP]   += 1
                Iconnections[IM[0]][DOWN_TOTAL]         += 1
                Mconnections[Mchiplet_id][UP_TOTAL]     += 1
            else:
                assert(level2 == level1+1)
                Iconnections[IM[0]][IM_CNT][UP]         += 1
                Mconnections[Mchiplet_id][IM_CNT][DOWN] += 1
                Iconnections[IM[0]][UP_TOTAL]           += 1
                Mconnections[Mchiplet_id][DOWN_TOTAL]   += 1
            
        # Now to determine router-router mapping
        # Create a tile for interposer for each II and IM connection
        # Get the stride information (to make tiles accordingly)
        # To determine the boundary routers.

        # Sanity Checks

        # Tetris-Style Tiling (Rules)
        # --> Allocate perimeters to the II connections
        # --> Any remaining routers to the IM connections
        # --> Each Router can be assumed to have Up/Down "valves"
        #       --> Upon allocation (remove from the graph)
        #       --> II connections can be spaced out 
        #           --> Intermediate routers are transparent in opposite direction
        #           --> (eg) if II in DOWN direction (between [0,3]:[3,4] --> occupying only the edges)
        #               then [1,3]:[2,4] are "transparent" (ready to use) in UP direction for IM connections.

        Ichiplet_tile_coords = [{} for _ in range(len(Iconnections))]

        for i in range(len(Iconnections)):
            IIs                     = Iconnections[i][II_CNT]
            IMs                     = Iconnections[i][IM_CNT]
            up_connections          = Iconnections[i][UP_TOTAL]
            down_connections        = Iconnections[i][DOWN_TOTAL]
            Ichiplet_id             = num_meshes + i
            Ichiplet_dim            = interposer_routers[Ichiplet_id][2]
            Ichiplet_num_routers    = Ichiplet_dim[0] * Ichiplet_dim[1]
            required_routers        = 4 * (up_connections + down_connections)
            assert(Ichiplet_num_routers >= required_routers)
            Ichiplet_tile_coords[i] = tetris_tile_build(IIs, IMs, Ichiplet_dim)


        # for i in range(len(Iconnections)):
        #     up, down            = Iconnections[i]
        #     req_bdry_routers    = 4 * (up + down)
        #     Ichiplet_id         = num_meshes + i
        #     Ichiplet_dim        = interposer_routers[Ichiplet_id][2]
        #     Ichiplet_routers    = Ichiplet_dim[0] * Ichiplet_dim[1]
        #     assert(Ichiplet_routers >= req_bdry_routers)

        # for i in range(Mconnections):
        #     up, down            = Mconnections[i]
        #     req_bdry_routers    = 4 * (up + down)
        #     Mchiplet_id         = i
        #     Mchiplet_dim        = mesh_routers[Mchiplet_id][2]
        #     Mchiplet_routers    = Mchiplet_dim[0] * Mchiplet_dim[1]
        #     assert(Mchiplet_routers > req_bdry_routers)
        
        # Chiplet mesh      --> N x N --> (N-1) connections to other meshes
        # Interposer mesh   --> N x M --> a) I-I ==> b) I-M ==> 
        interposer_bdry_routers = {}
        mesh_bdry_routers = {}
    
    def tetris_tile_build(IIs, IMs, Ichiplet_dim):
        no_IIs = True
        no_IMs = True
        UP = 0
        DOWN = 1

        if IIs[UP] != 0 or IIs[DOWN] != 0:
            no_IIs = False

        if IMs[UP] !=0 or IMs[DOWN] != 0:
            no_IMs = False
        
        assert(no_IIs == False or no_IMs == False, "Atleast one type of conenction per interposer required. Either IIs or IMs")
        Ichiplet_coords = []
        Irows = Ichiplet_dim[0]
        Icols = Ichiplet_dim[1]
        Iarea = Irows * Icols

        if(no_IIs == True):
            #TODO: Geometric decomposition
            x = 1
        
        elif(no_IMs == True):
            #TODO: Geomteric decomposition
            x = 2
        
        else:
            #TODO: Tetris-Style allocation