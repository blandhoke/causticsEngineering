using Pkg
Pkg.activate(".")

using Images, CausticsEngineering

image = Images.load("./examples/circle_target.png") # Check current working directory with pwd()
engineer_caustics(image);
