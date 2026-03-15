# Currently unused.
const grid_definition = 512


"""
$(SIGNATURES)

This func returns a square mesh, centered on zero, with (width * height) nodes
"""
function squareMesh(width::Int, height::Int)
    nodeList = Vector{Point3D}(undef, height * width)
    nodeArray = Matrix{Point3D}(undef, width, height)
    count = 1
    midpoint = width / 2
    for y in 1:height, x in 1:width
        newPoint = Point3D(x, y, 0, x, y)
        nodeList[count] = newPoint
        nodeArray[x, y] = newPoint
        count += 1
    end

    triangles = Vector{Triangle}(undef, (width - 1) * (height - 1) * 2)
    count = 1
    for y = 1:(height - 1)
        for x = 1:(width - 1)
            # here x and y establish the column of squares we're in
            index_ul = (y - 1) * width + x
            index_ur = index_ul + 1

            index_ll = y * width + x
            index_lr = index_ll + 1

            triangles[count] = Triangle(index_ul, index_ll, index_ur)
            count += 1
            triangles[count] = Triangle(index_lr, index_ur, index_ll)
            count += 1
        end
    end

    return Mesh(nodeList, nodeArray, triangles, width, height)
end


"""
$(SIGNATURES)

Warning: not guaranteed to work in 3D?
"""
function centroid(mesh::Mesh, index::Int)
    triangle = mesh.triangles[index]
    p1 = mesh.nodes[triangle.pt1]
    p2 = mesh.nodes[triangle.pt2]
    p3 = mesh.nodes[triangle.pt3]

    return centroid(p1, p2, p3)
end


"""
$(SIGNATURES)

Given 3 points and 3 velocities, calculate the `t` required to bring the area of that triangle to zero
"""
function findT(
    p1::Point3D,
    p2::Point3D,
    p3::Point3D,
    dp1::Point3D,
    dp2::Point3D,
    dp3::Point3D,
)
    x1 = p2.x - p1.x
    y1 = p2.y - p1.y

    x2 = p3.x - p1.x
    y2 = p3.y - p1.y

    u1 = dp2.x - dp1.x
    v1 = dp2.y - dp1.y

    u2 = dp3.x - dp1.x
    v2 = dp3.y - dp1.y

    a = u1 * v2 - u2 * v1
    b = x1 * v1 + y2 * u1 - x2 * v1 - y1 * u2
    c = x1 * y2 - x2 * y1

    if a != 0
        quotient = b^2 - 4a * c
        if quotient >= 0
            d = sqrt(quotient)
            return (-b - d) / 2a, (-b + d) / 2a
        else
            return -123.0, -123.0
        end
    else

        # cool, there just isn't any dependence on t^2, but there is still on t!
        return -c / b, -c / b
    end
end


"""
$(SIGNATURES)

This function saves the mesh object in obj format.
"""
function saveObj!(mesh::Mesh, filename::String; scale=1.0, scalez=1.0, reverse=false, flipxy=false)
    # This function saves the mesh object in stl format
    open(filename, "w") do io
        for vertex in mesh.nodes
            if flipxy
                println(io, "v ", vertex.y * scale, " ", vertex.x * scale, " ", vertex.z * scalez)
            else
                println(io, "v ", vertex.x * scale, " ", vertex.y * scale, " ", vertex.z * scalez)
            end
        end
  
        for face in mesh.triangles
            if reverse
                println(io, "f ", face.pt3, " ", face.pt2, " ", face.pt1)
            else
                println(io, "f ", face.pt1, " ", face.pt2, " ", face.pt3)
            end
        end
  
        println(io, "dims ", mesh.width, " ", mesh.height)
    end
end


"""
$(SIGNATURES)
"""
function Obj2Mesh(filename)
    lines = readlines(filename)

    vertexLines = [l for l in lines if startswith(l, "v")]
    nodeList = Vector{Point3D}(undef, size(vertexLines))
    count = 1

    for line in vertexLines
        elements = split(line, " ")
        x = parse(Float64, elements[2])
        y = parse(Float64, elements[3])
        z = parse(Float64, elements[4]) * 10
        pt = Point3D(x, y, z, 0, 0)
        nodeList[count] = pt
        count += 1
    end

    faceLines = [l for l in lines if startswith(l, "f")]
    triangles = Vector{Triangle}(undef, size(faceLines))
    for line in faceLines
        elements = split(line, " ")
        triangle = Triangle(
            parse(Int64, elements[2]),
            parse(Int64, elements[3]),
            parse(Int64, elements[4]),
        )
    end

    dimsLines = [l for l in lines if startswith(l, "dims")]
    elements = split(dimsLines[1], " ")

    return Mesh(nodeList, triangles, parse(Int64, elements[2]), parse(Int64, elements[3]))
end


"""
$(SIGNATURES)
"""
function ∇(f::Matrix{Float64})
    width, height = size(f)

    ∇fᵤ = zeros(Float64, width, height)   # the right edge will be filled with zeros
    ∇fᵥ = zeros(Float64, width, height)   # the buttom edge will be filled with zeros

    @inbounds for y in 1:height, x in 1:width
        ∇fᵤ[x, y] = (x == width ? 0.0 : f[x + 1, y] - f[x, y])
        ∇fᵥ[x, y] = (y == height ? 0.0 : f[x, y + 1] - f[x, y])
    end

    return ∇fᵤ, ∇fᵥ
end


"""
$(SIGNATURES)
"""
function getPixelArea(mesh::Mesh)
    # A Mesh is a grid of 3D points. The X and Y coordinates are not necessarily aligned or square
    # The Z coordinate represents the value. brightness is just proportional to area.
    # pixelAreas = Matrix{Float64}(undef, mesh.width - 1, mesh.height - 1)
    pixelAreas = zeros(mesh.width - 1, mesh.height - 1)

    @inbounds for y in 1:mesh.height - 1, x in 1:mesh.width - 1
        upperLeft  = mesh.nodeArray[x,     y    ]
        upperRight = mesh.nodeArray[x + 1, y    ]
        lowerLeft  = mesh.nodeArray[x,     y + 1]
        lowerRight = mesh.nodeArray[x + 1, y + 1]

        #=
        *------*
        |    / |
        |   /  |
        |  /   |
        | /    |
        *------* =#
        pixelAreas[x, y] =
            triangle_area_2d(lowerLeft, upperRight, upperLeft) +
            triangle_area_2d(lowerLeft, lowerRight, upperRight)
    end

    return pixelAreas
end


"""
$(SIGNATURES)
"""
function relax!(matrix::Matrix{Float64}, D::Matrix{Float64})
    # Successive over-relaxation with Neumann boundary conditions (zero derivative at boundary).
    # See: https://math.stackexchange.com/questions/3790299/how-to-iteratively-solve-poissons-equation-with-no-boundary-conditions
    # Boundary cases are handled separately so the interior hot loop is branch-free.
    width, height = size(matrix)
    ω = 1.99
    max_update = 0.0

    # Corners (2 neighbors each)
    @inbounds begin
        delta = ω / 2 * (matrix[1, 2] + matrix[2, 1] - 2matrix[1, 1] - D[1, 1])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[1, 1] += delta

        delta = ω / 2 * (matrix[1, height-1] + matrix[2, height] - 2matrix[1, height] - D[1, height])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[1, height] += delta

        delta = ω / 2 * (matrix[width, 2] + matrix[width-1, 1] - 2matrix[width, 1] - D[width, 1])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[width, 1] += delta

        delta = ω / 2 * (matrix[width, height-1] + matrix[width-1, height] - 2matrix[width, height] - D[width, height])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[width, height] += delta
    end

    # Left edge x=1, y=2..height-1 (3 neighbors)
    @inbounds for y = 2:height-1
        delta = ω / 3 * (matrix[1, y-1] + matrix[1, y+1] + matrix[2, y] - 3matrix[1, y] - D[1, y])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[1, y] += delta
    end

    # Right edge x=width, y=2..height-1 (3 neighbors)
    @inbounds for y = 2:height-1
        delta = ω / 3 * (matrix[width, y-1] + matrix[width, y+1] + matrix[width-1, y] - 3matrix[width, y] - D[width, y])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[width, y] += delta
    end

    # Top edge y=1, x=2..width-1 (3 neighbors)
    @inbounds for x = 2:width-1
        delta = ω / 3 * (matrix[x, 2] + matrix[x-1, 1] + matrix[x+1, 1] - 3matrix[x, 1] - D[x, 1])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[x, 1] += delta
    end

    # Bottom edge y=height, x=2..width-1 (3 neighbors)
    @inbounds for x = 2:width-1
        delta = ω / 3 * (matrix[x, height-1] + matrix[x-1, height] + matrix[x+1, height] - 3matrix[x, height] - D[x, height])
        abs(delta) > max_update && (max_update = abs(delta))
        matrix[x, height] += delta
    end

    # Interior: branch-free inner loop (4 neighbors)
    @inbounds for y = 2:height-1
        for x = 2:width-1
            delta = ω / 4 * (matrix[x, y-1] + matrix[x, y+1] + matrix[x-1, y] + matrix[x+1, y] - 4matrix[x, y] - D[x, y])
            if abs(delta) > max_update
                max_update = abs(delta)
            end
            matrix[x, y] += delta
        end
    end

    return max_update
end


"""
$(SIGNATURES)

This function will take a `grid_definition x grid_definition` matrix and returns a `grid_definition x grid_definition` mesh.

It currently takes the size of the matrix passed as argument.
"""
function matrix_to_mesh(matrix::Matrix{Float64})
    w, h = size(matrix)

    retval = squareMesh(w, h)
    for x in 1:w, y in 1:h
        index = (y - 1) * retval.width + x
        node = retval.nodes[index]
        node.z = matrix[x, y]
    end

    return retval
end


"""
$(SIGNATURES)
"""
function marchMesh!(mesh::Mesh, ϕ::Matrix{Float64})
    ∇ϕᵤ, ∇ϕᵥ = ∇(ϕ)

    # Use two Float64 matrices instead of Matrix{Point3D} — avoids heap allocation
    # of width*height mutable structs and gives cache-friendly access patterns.
    vel_u = zeros(Float64, mesh.width, mesh.height)
    vel_v = zeros(Float64, mesh.width, mesh.height)

    @inbounds for y in 1:mesh.height, x in 1:mesh.width
        u = (x == mesh.width) ? 0.0 :
            (y == mesh.height ? ∇ϕᵤ[x, y - 1] : ∇ϕᵤ[x, y])
        v = (y == mesh.height) ? 0.0 :
            (x == mesh.width ? ∇ϕᵥ[x - 1, y] : ∇ϕᵥ[x, y])
        vel_u[x, y] = -u
        vel_v[x, y] = -v
    end

    min_t = 10000.0
    @inbounds for triangle in mesh.triangles
        p1 = mesh.nodes[triangle.pt1]
        p2 = mesh.nodes[triangle.pt2]
        p3 = mesh.nodes[triangle.pt3]

        v1 = Point3D(vel_u[p1.ix, p1.iy], vel_v[p1.ix, p1.iy], 0.0, 0, 0)
        v2 = Point3D(vel_u[p2.ix, p2.iy], vel_v[p2.ix, p2.iy], 0.0, 0, 0)
        v3 = Point3D(vel_u[p3.ix, p3.iy], vel_v[p3.ix, p3.iy], 0.0, 0, 0)

        t1, t2 = findT(p1, p2, p3, v1, v2, v3)

        0 < t1 < min_t && (min_t = t1)
        0 < t2 < min_t && (min_t = t2)
    end

    println("Overall min_t:", min_t)
    δ = min_t / 2

    @inbounds for point in mesh.nodes
        point.x += vel_u[point.ix, point.iy] * δ
        point.y += vel_v[point.ix, point.iy] * δ
    end
end


    """
$(SIGNATURES)
"""
function quantifyLoss!(D, suffix, img)
    println("Loss:")
    println("Minimum: $(minimum(D))")
    println("Maximum: $(maximum(D))")
    println("SUM: $(sum(D))")

    blue = zeros(size(D))
    blue[D .> 0] = D[D .> 0]
    red = zeros(size(D))
    red[D .< 0] = -D[D .< 0]
    green = zeros(size(D))

    println(size(blue))
    println(size(red))
    println(size(green))

    rgbImg = RGB.(red, green, blue)'
    save("./examples/loss_$(suffix).png", map(clamp01nan, rgbImg))
end


"""
$(SIGNATURES)

For each mesh cell, sample `img` at the centroid of the *deformed* cell via bilinear
interpolation. This is the Damberg & Heidrich (2015) RHS correction: rather than comparing
pixel areas against the fixed target grid, we pull the target back through the current
mapping so the Poisson solver accounts for accumulated geometric distortion.
"""
function warpTarget(mesh::Mesh, img::Matrix)
    imgWidth, imgHeight = size(img)
    warped = zeros(Float64, mesh.width - 1, mesh.height - 1)

    @inbounds for y in 1:mesh.height - 1, x in 1:mesh.width - 1
        ul = mesh.nodeArray[x,     y    ]
        ur = mesh.nodeArray[x + 1, y    ]
        ll = mesh.nodeArray[x,     y + 1]
        lr = mesh.nodeArray[x + 1, y + 1]

        # Centroid of the deformed cell in image coordinates
        cx = clamp((ul.x + ur.x + ll.x + lr.x) / 4, 1.0, Float64(imgWidth))
        cy = clamp((ul.y + ur.y + ll.y + lr.y) / 4, 1.0, Float64(imgHeight))

        # Bilinear interpolation
        xi  = floor(Int, cx);  xi1 = min(xi + 1, imgWidth)
        yi  = floor(Int, cy);  yi1 = min(yi + 1, imgHeight)
        fx  = cx - xi;         fy  = cy - yi

        warped[x, y] = (1 - fx) * (1 - fy) * Float64(img[xi,  yi ]) +
                            fx  * (1 - fy) * Float64(img[xi1, yi ]) +
                       (1 - fx) *      fy  * Float64(img[xi,  yi1]) +
                            fx  *      fy  * Float64(img[xi1, yi1])
    end

    return warped
end


"""
$(SIGNATURES)
"""
function oneIteration(meshy, img, suffix)
    # Remember meshy is (will be) `grid_definition x grid_definition` just like the image
    # `grid_definition x grid_definition`, so LJ is `grid_definition x grid_definition`.
    LJ = getPixelArea(meshy)
    # Pull target back through the current mapping (Damberg & Heidrich 2015)
    warpedImg = warpTarget(meshy, img)
    D = Float64.(LJ - warpedImg)
    # Shift D to ensure its sum is zero
    width, height = size(img)
    D .-= sum(D) / (width * height)

    # Save the loss image as a png
    println(minimum(D))
    println(maximum(D))
    quantifyLoss!(D, suffix, img)

    # These lines are just for plotting the quiver of L, which I needed for the blog post
    # ∇Lᵤ, ∇Lᵥ = ∇(D)
    # plotVAsQuiver(∇Lᵤ, ∇Lᵥ, stride=10, scale=10, max_length=200)
    # println("okay")
    # return

    width, height = size(img)

    ϕ = zeros(width, height)

    println("Building Phi")
    for i = 1:10000
        max_update = relax!(ϕ, D)
        
        if isnan(max_update)
            println("MAX UPDATE WAS NaN. CANNOT BUILD PHI")
            return
        end
        
        if i % 500 == 0
            println(max_update)
        end

        if max_update < 0.00001
            println("Convergence reached at step $(i) with max_update of $(max_update)")
            break
        end
    end

    # saveObj!(
    #     matrix_to_mesh(ϕ * 0.02),
    #     "./examples/phi_$(suffix).obj",
    #     reverse=false,
    #     flipxy=true,
    # )
    # plotAsQuiver(ϕ * -1.0, stride=30, scale=1.0, max_length=200, flipxy=true, reversex=false, reversey=false)
    # saveObj(matrix_to_mesh(D * 10), "D_$(suffix).obj")

    # Now we need to march the x,y locations in our mesh according to this gradient!
    marchMesh!(meshy, ϕ)
# saveObj!(meshy, "./examples/mesh_$(suffix).obj", flipxy=true)
end


"""
$(SIGNATURES)
"""
function setHeights!(mesh, heights, heightScale=1.0, heightOffset=10)
    width, height = size(heights)
    for y = 1:height
        for x = 1:width
            mesh.nodeArray[x, y].z = heights[x, y] * heightScale + heightOffset
            if x == 100 && y == 100
                println("Example heights: $(heights[x, y])  and  $(heights[x, y] * heightScale) and $(heights[x, y] * heightScale + heightOffset)")
            end
        end
    end

    # get the side edge
    for y = 1:height
        mesh.nodeArray[width + 1, y].z = mesh.nodeArray[width, y].z
    end

    # get the bottom edge
    for x = 1:width + 1
        mesh.nodeArray[x, height + 1].z = mesh.nodeArray[x, height].z
    end


    # # get the pesky corner!
# mesh.nodeArray[width + 1, height + 1].z = mesh.nodeArray[width, height].z
end


"""
$(SIGNATURES)
"""
function solidify(inputMesh, offset=100)
    width = inputMesh.width
    height = inputMesh.height
    totalNodes = width * height * 2
    nodeList = Vector{Point3D}(undef, totalNodes)
    nodeArrayTop = Matrix{Point3D}(undef, width, height)
    nodeArrayBottom = Matrix{Point3D}(undef, width, height)

    # imagine a 4x4 image. 4 * 2 + 2 * 2 = 12
    numEdgeNodes = width * 2 + (height - 2) * 2

    numTrianglesTop = (width - 1) * (height - 1) * 2
    numTrianglesBottom = numTrianglesTop
    numTrianglesEdges = numEdgeNodes * 2

    totalTriangles = numTrianglesBottom + numTrianglesTop + numTrianglesEdges

    println("Specs: $(width)  $(height)  $(totalNodes)  $(numEdgeNodes)  $(numTrianglesBottom) $(totalTriangles)")

    # Build the bottom surface
    count = 1
    for y = 1:height
        for x = 1:width
            newPoint = Point3D(x, y, -offset, x, y)
            nodeList[count] = newPoint
            nodeArrayBottom[x, y] = newPoint
            count += 1
        end
    end

    # Copy in the top surface
    for y = 1:height
        for x = 1:width
            node = inputMesh.nodeArray[x, y]
            copiedPoint = Point3D(node.x, node.y, node.z, node.ix, node.iy)
            if node.ix != x
                println("OH NO POINTS NOT MATCHED $(x) vs $(node.ix)")
            end
            if node.iy != y
                println("OH NO POINTS NOT MATCHED $(y) vs $(node.iy)")
            end

            nodeList[count] = copiedPoint
            nodeArrayTop[x, y] = copiedPoint
            count += 1
        end
    end

    println("We now have $(count - 1) valid nodes")

    triangles = Vector{Triangle}(undef, totalTriangles)
    # Build the triangles for the bottom surface
    count = 1
    for y = 1:(height - 1)
        for x = 1:(width - 1)
          # here x and y establish the column of squares we're in
            index_ul = (y - 1) * width + x
            index_ur = index_ul + 1

            index_ll = y * width + x
            index_lr = index_ll + 1

            triangles[count] = Triangle(index_ul, index_ll, index_ur)
            count += 1
            triangles[count] = Triangle(index_lr, index_ur, index_ll)
            count += 1
        end
    end

    println("We've filled up $(count - 1) triangles")
    if count != numTrianglesBottom + 1
        println("Hmm aren't count and triangles bottom equal? $(count) vs $(numTrianglesBottom + 1)")
        end

    # Build the triangles for the top surface
    for y = 1:(height - 1)
        for x = 1:(width - 1)
          # here x and y establish the column of squares we're in
            index_ul = (y - 1) * width + x + totalNodes / 2
            index_ur = index_ul + 1

            index_ll = y * width + x + totalNodes / 2
            index_lr = index_ll + 1

            triangles[count] = Triangle(index_ul, index_ur, index_ll)
            count += 1
            triangles[count] = Triangle(index_lr, index_ll, index_ur)
            count += 1
        end
    end

    println("We've filled up $(count - 1) triangles")

    # Build the triangles to close the mesh
    x = 1
    for y = 1:(height - 1)
        ll = (y - 1) * width + x
        ul = ll + totalNodes / 2
        lr = y * width + x
        ur = lr + totalNodes / 2
        triangles[count] = Triangle(ll, ul, ur)
        count += 1
    triangles[count] = Triangle(ur, lr, ll)
        count += 1
    end

    x = width
    for y = 1:(height - 1)
        ll = (y - 1) * width + x
        ul = ll + totalNodes / 2
        lr = y * width + x
        ur = lr + totalNodes / 2
        triangles[count] = Triangle(ll, ur, ul)
        count += 1
        triangles[count] = Triangle(ur, ll, lr)
        count += 1
    end

    y = 1
    for x = 2:width
        ll = (y - 1) * width + x
        ul = ll + totalNodes / 2
        lr = (y - 1) * width + (x - 1)
        ur = lr + totalNodes / 2
        triangles[count] = Triangle(ll, ul, ur)
        count += 1
        triangles[count] = Triangle(ur, lr, ll)
        count += 1
    end

    y = height
    for x = 2:width
        ll = (y - 1) * width + x
        ul = ll + totalNodes / 2
        lr = (y - 1) * width + (x - 1)
        ur = lr + totalNodes / 2
        triangles[count] = Triangle(ll, ur, ul)
        count += 1
        triangles[count] = Triangle(ur, ll, lr)
        count += 1
    end

Mesh(nodeList, nodeArrayBottom, triangles, width, height)
end


"""
$(SIGNATURES)
"""
function findSurface(mesh, image, f, imgWidth)
    width, height = size(image)

    # imgWidth = .1 # m
    # f = 1.0  # m
    H = f
    metersPerPixel = imgWidth / width
    println(metersPerPixel)

    # η = 1.49
    n₂ = 1
    n₁ = 1.49
    inv_n1m1 = 1.0 / (n₁ - 1)   # precompute: avoids division inside hot loop
    Nx = zeros(width + 1, height + 1)
    Ny = zeros(width + 1, height + 1)

    @inbounds for j = 1:height
        for i = 1:width
            node = mesh.nodeArray[i, j]
            dx = (node.ix - node.x) * metersPerPixel
            dy = (node.iy - node.y) * metersPerPixel

            dz = H - node.z * metersPerPixel

            Nx[i, j] = tan(atan(dx / dz) * inv_n1m1)
            Ny[i, j] = tan(atan(dy / dz) * inv_n1m1)
        end
    end

    divergence = zeros(width, height)
    # We need to find the divergence of the Vector field described by Nx and Ny

    @inbounds for j = 1:height
        for i = 1:width
            divergence[i, j] = (Nx[i + 1, j] - Nx[i, j]) + (Ny[i, j + 1] - Ny[i, j])
        end
    end
    println("Have all the divergences")
    println("Divergence sum: $(sum(divergence))")
    divergence .-= sum(divergence) / (width * height)

    h = zeros(width, height)
    max_update = 0
    for i = 1:10000
        max_update = relax!(h, divergence)

        if i % 500 == 0
            println(max_update)
        end
        if max_update < 0.00001
            println("Convergence reached at step $(i) with max_update of $(max_update)")
            break
        end
    end

    # println("HEIGHT STATS")
    # h .-= sum(h) / (width * height)
    # println(minimum(h))
    # println(maximum(h))
    # println(sum(h))
    # println("-----------")

    # saveObj!(matrix_to_mesh(h * 10), "examples/heightmap.obj")
    h, metersPerPixel
end
    
"""
$(SIGNATURES)
"""
function testSquareMesh!()
    mesh = squareMesh(100, 50)

    println(mesh.nodeArray[1, 1])
    println(mesh.nodes[1])

    mesh.nodeArray[1, 1].x = 8
    println(mesh.nodeArray[1, 1])
    println(mesh.nodes[1])

    mesh.nodes[1].y += 12
println(mesh.nodeArray[1, 1])
    println(mesh.nodes[1])

end


"""
$(SIGNATURES)
"""
function testSolidify!()
    println("Testing solidification")
    width = 100
    height = 100
    origMesh = squareMesh(width, height)

    for y in 1:height, x in 1:width
        x2 = (x - width / 2) / width
        y2 = (y - height / 2) / height
        value = x2 * x2 + y2 * y2
        origMesh.nodeArray[x, y].z = 15 - value * 25
    end

    saveObj!(origMesh, "./examples/testSolidify.obj")
    solidMesh = solidify(origMesh, 0)
    saveObj!(solidMesh, "./examples/testSolidify2.obj")
end


"""
$(SIGNATURES)
"""
function plotAsQuiver(
    g;
    stride=4,
    scale=300,
    max_length=2,
    flipxy=false,
    reversey=false,
    reversex=false,
)
    h, w = size(g)
    xs = Float64[]
    ys = Float64[]
    us = Float64[]
    vs = Float64[]

    for x in 1:stride:w, y in 1:stride:h
        reversex ? push!(xs, x) : push!(xs, -x)
        reversey ? push!(ys, -y) : push!(ys, y)

        p1 = g[y, x]
        u = (g[y, x + 1] - g[y, x]) * scale
        v = (g[y + 1, x] - g[y, x]) * scale

        u = -u

        reversey && (v = -v)
        reversex && (u = -u)

        # println(u, v)
        u >= 0 ? push!(us, min(u, max_length)) : push!(us, max(u, -max_length))
        v >= 0 ? push!(vs, min(v, max_length)) : push!(vs, max(v, -max_length))
    end

    q =
        flipxy ? quiver(ys, xs, quiver=(vs, us), aspect_ratio=:equal) :
        quiver(xs, ys, quiver=(us, vs), aspect_ratio=:equal)

    display(q)
    readline()
end


"""
$(SIGNATURES)
"""
function plotVAsQuiver(vx, vy; stride=4, scale=300, max_length=2)
    h, w = size(vx)

    xs = Float64[]
    ys = Float64[]
    us = Float64[]
    vs = Float64[]

    for x in 1:stride:w, y in 1:stride:h
        push!(xs, x)
        push!(ys, h - y)

        u = max(vx[x, y], 0.001)
        v = max(vy[x, y], 0.001)

        push!(us, u)
        push!(vs, v)
        # println(u, ": ", v)
    end

    # readline()
    q = quiver(xs, ys, quiver=(us, vs), aspect_ratio=:equal)
    display(q)
    readline()
end



"""
$(SIGNATURES)
"""
function engineer_caustics(img)
    img = Gray.(img)
    img2 = permutedims(img) * 1.0
    width, height = size(img2)

    # meshy is the same size as the image
    meshy = squareMesh(width + 1, height + 1)

    # We need to boost the brightness of the image so that its sum and the sum of the area are equal
    mesh_sum = width * height
    image_sum = sum(img2)
    boost_ratio = mesh_sum / image_sum

    # img3 is `grid_definition x grid_definition` and is normalised to the same (sort of) _energy_ as the
    # original image.
    img3 = img2 .* boost_ratio

    oneIteration(meshy, img3, "it1")
    oneIteration(meshy, img3, "it2")
    oneIteration(meshy, img3, "it3")
    oneIteration(meshy, img3, "it4")
    oneIteration(meshy, img3, "it5")
    oneIteration(meshy, img3, "it6")

    artifactSize = 0.1  # meters
    focalLength = 0.2 # meters
    h, metersPerPixel = findSurface(meshy, img3, focalLength, artifactSize)

    setHeights!(meshy, h, 1.0, 10)

    solidMesh = solidify(meshy)
    saveObj!(
        solidMesh,
        "./examples/original_image.obj",
        scale=1 / 512 * artifactSize,
        scalez=1 / 512.0 * artifactSize,
    )

    return meshy, img3
end


"""
$(SIGNATURES)
"""
function main()
    @assert size(ARGS) == (1,) "Intented usage is: julia create_mesh.jl image.png"

    img = load(ARGS[1])
    return engineer_caustics(img)
end


"""
$(SIGNATURES)
"""
main()
