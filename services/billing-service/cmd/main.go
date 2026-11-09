package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
)

func main() {
	app := fiber.New()

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok", "service": "srave-billing"})
	})

	// TODO: register billing routes
	// handlers.RegisterBillingRoutes(app)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8002"
	}
	log.Fatal(app.Listen(":" + port))
}
