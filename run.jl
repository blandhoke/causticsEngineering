using Pkg
Pkg.activate(".")

using Images, CausticsEngineering

image = Images.load("./examples/befuddled_cow_solver_input.jpg") # Check current working directory with pwd()
engineer_caustics(image);
