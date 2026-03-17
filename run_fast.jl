using Pkg; Pkg.activate(".")
using Images, CausticsEngineering

TARGET_IMAGE = get(ENV, "COW2_INPUT", "./examples/befuddled_cow_solver_input.jpg")
println("Loading: $TARGET_IMAGE")
image = Images.load(TARGET_IMAGE)
image = imresize(image, (256, 256))
println("Resized to 256x256 — mesh will be ~131k faces")
engineer_caustics(image)
