using Pkg; Pkg.activate(".")
using Images, CausticsEngineering

TARGET_IMAGE = get(ENV, "COW2_INPUT", "./examples/befuddled_cow_solver_input.jpg")
println("Loading: $TARGET_IMAGE")
image = Images.load(TARGET_IMAGE)
image = imresize(image, (1024, 1024))
println("Resized to 1024x1024 — mesh will be ~2.1M faces")
engineer_caustics(image)
